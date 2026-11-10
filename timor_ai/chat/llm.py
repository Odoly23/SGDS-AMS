"""
Pembungkus model bahasa (LLM).

Dua backend (diatur lewat LLM_BACKEND di .env):
  dummy -> tidak memuat model; berguna untuk tes alur aplikasi di laptop apa pun.
  hf    -> Hugging Face Transformers (default Gemma 2 2B-it) + adapter LoRA opsional.

Model dimuat SEKALI saja (lazy, thread-safe) lalu dipakai ulang di semua request.
"""
import logging
import threading
from dataclasses import dataclass

from django.conf import settings

from . import prompts

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_state = {"model": None, "tokenizer": None}


class LLMUnavailable(Exception):
    """Model tidak bisa dipanggil (kunci salah, kuota habis, jaringan). Pesan aman untuk user; user TIDAK ditagih."""


@dataclass
class LLMResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


def model_name() -> str:
    cfg = settings.LAFEX_AI
    if cfg["LLM_BACKEND"] == "dummy":
        return "dummy"
    if cfg["LLM_BACKEND"] == "anthropic":
        return cfg["ANTHROPIC_MODEL"]
    return cfg["LLM_MODEL_ID"] + (f"+lora:{cfg['LLM_LORA_PATH']}" if cfg["LLM_LORA_PATH"] else "")


def _load():
    """Muat model & tokenizer sekali saja."""
    with _lock:
        if _state["model"] is not None:
            return _state["model"], _state["tokenizer"]
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        cfg = settings.LAFEX_AI
        token = cfg["HF_TOKEN"] or None  # Gemma butuh token + setuju lisensi di huggingface.co
        logger.info("Memuat model %s ...", cfg["LLM_MODEL_ID"])
        tokenizer = AutoTokenizer.from_pretrained(cfg["LLM_MODEL_ID"], token=token)
        use_cuda = torch.cuda.is_available()
        # bfloat16 = ~5 GB RAM untuk Gemma 2 2B (float32 butuh ~10 GB). Gemma 2 sebaiknya tidak pakai float16.
        dtype = getattr(torch, cfg["LLM_DTYPE"], torch.bfloat16)
        model = AutoModelForCausalLM.from_pretrained(
            cfg["LLM_MODEL_ID"],
            token=token,
            torch_dtype=dtype,
            device_map="auto" if use_cuda else None,
        )
        if cfg["LLM_LORA_PATH"]:
            from peft import PeftModel

            model = PeftModel.from_pretrained(model, cfg["LLM_LORA_PATH"])
        model.eval()
        _state["model"], _state["tokenizer"] = model, tokenizer
        return model, tokenizer


def _merge_system(messages: list[dict]) -> list[dict]:
    """Gemma tidak mendukung role 'system' -> tempelkan ke pesan user pertama."""
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [dict(m) for m in messages if m["role"] != "system"]
    if system and rest and rest[0]["role"] == "user":
        rest[0]["content"] = f"{system}\n\n---\n{rest[0]['content']}"
    return rest


def generate(messages: list[dict], max_new_tokens: int = None) -> str:
    """Versi sederhana: hanya teks jawaban."""
    return generate_full(messages, max_new_tokens).text


def generate_full(messages: list[dict], max_new_tokens: int = None) -> LLMResult:
    """
    messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
    Return: LLMResult(text, input_tokens, output_tokens) - jumlah token dipakai untuk penagihan poin.
    """
    cfg = settings.LAFEX_AI
    if cfg["LLM_BACKEND"] == "dummy":
        text = _dummy_answer(messages)
        # perkiraan kasar (1 token ~ 4 karakter) supaya sistem poin bisa dicoba tanpa model
        return LLMResult(text, sum(len(m["content"]) for m in messages) // 4, len(text) // 4)
    if cfg["LLM_BACKEND"] == "anthropic":
        return _anthropic_generate(messages, max_new_tokens)
    return _hf_generate(messages, max_new_tokens)


_client = None


def _anthropic_generate(messages: list[dict], max_new_tokens: int = None) -> LLMResult:
    """Panggil model berbayar lewat API resmi. Dipanggil dari server; kunci API tidak pernah dikirim ke browser."""
    import anthropic

    global _client
    cfg = settings.LAFEX_AI
    if not cfg["ANTHROPIC_API_KEY"]:
        raise LLMUnavailable("Layanan AI belum dikonfigurasi.")
    if _client is None:
        _client = anthropic.Anthropic(api_key=cfg["ANTHROPIC_API_KEY"], timeout=60.0, max_retries=2)

    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    convo = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
    kwargs = {}
    if system:
        kwargs["system"] = system
    if cfg["ANTHROPIC_EFFORT"]:
        kwargs["output_config"] = {"effort": cfg["ANTHROPIC_EFFORT"]}   # low = lebih hemat token "berpikir"
    # catatan: max_tokens juga menampung token berpikir, jadi nilainya sengaja lebih besar dari jawaban yang diharapkan
    max_tokens = max(cfg["ANTHROPIC_MAX_TOKENS"], max_new_tokens or 0)
    try:
        resp = _client.messages.create(model=cfg["ANTHROPIC_MODEL"], max_tokens=max_tokens, messages=convo, **kwargs)
    except anthropic.AuthenticationError:
        logger.error("ANTHROPIC_API_KEY ditolak")
        raise LLMUnavailable("Layanan AI sedang bermasalah. Coba lagi nanti.")
    except anthropic.RateLimitError:
        raise LLMUnavailable("Layanan AI sedang ramai. Coba lagi sebentar lagi.")
    except anthropic.APIStatusError as exc:
        logger.error("Anthropic API %s: %s", exc.status_code, exc.message)
        raise LLMUnavailable("Layanan AI sedang bermasalah. Coba lagi nanti.")
    except anthropic.APIConnectionError:
        raise LLMUnavailable("Tidak bisa terhubung ke layanan AI. Coba lagi nanti.")

    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if resp.stop_reason == "refusal":
        text = prompts.REFUSAL
    elif not text:
        text = prompts.EMPTY_ANSWER
    u = resp.usage
    tokens_in = (u.input_tokens or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0)
    return LLMResult(text, tokens_in, u.output_tokens or 0)


def _hf_generate(messages: list[dict], max_new_tokens: int = None) -> LLMResult:
    cfg = settings.LAFEX_AI
    import torch

    model, tokenizer = _load()
    chat = _merge_system(messages)
    input_ids = tokenizer.apply_chat_template(chat, add_generation_prompt=True, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens or cfg["MAX_NEW_TOKENS"],
            do_sample=True,
            temperature=0.4,   # rendah = lebih patuh pada konteks, kurang berhalusinasi
            top_p=0.9,
            repetition_penalty=1.1,
        )
    text = tokenizer.decode(output[0][input_ids.shape[-1]:], skip_special_tokens=True).strip()
    return LLMResult(text, int(input_ids.shape[-1]), int(output.shape[-1] - input_ids.shape[-1]))


def _dummy_answer(messages: list[dict]) -> str:
    """Jawaban palsu: menampilkan potongan konteks RAG supaya Anda bisa cek retrieval-nya."""
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    ctx = system.split("KONTEKS:", 1)[-1].strip() if "KONTEKS:" in system else ""
    if ctx and prompts.NO_CONTEXT not in ctx:
        return f"{prompts.FALLBACK_NO_MODEL}\n\nKonteks yang ditemukan untuk pertanyaan \"{user[:80]}\":\n{ctx[:600]}"
    return f"{prompts.FALLBACK_NO_MODEL}\n\nPesan Anda: {user[:200]}"
