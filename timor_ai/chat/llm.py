"""
Pembungkus model bahasa (LLM).

Dua backend (diatur lewat LLM_BACKEND di .env):
  dummy -> tidak memuat model; berguna untuk tes alur aplikasi di laptop apa pun.
  hf    -> Hugging Face Transformers (default Gemma 2 2B-it) + adapter LoRA opsional.

Model dimuat SEKALI saja (lazy, thread-safe) lalu dipakai ulang di semua request.
"""
import logging
import threading

from django.conf import settings

from . import prompts

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_state = {"model": None, "tokenizer": None}


def model_name() -> str:
    cfg = settings.LAFEX_AI
    if cfg["LLM_BACKEND"] == "dummy":
        return "dummy"
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
    """
    messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
    Return: teks jawaban.
    """
    cfg = settings.LAFEX_AI
    if cfg["LLM_BACKEND"] == "dummy":
        return _dummy_answer(messages)

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
    return tokenizer.decode(output[0][input_ids.shape[-1]:], skip_special_tokens=True).strip()


def _dummy_answer(messages: list[dict]) -> str:
    """Jawaban palsu: menampilkan potongan konteks RAG supaya Anda bisa cek retrieval-nya."""
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    ctx = system.split("KONTEKS:", 1)[-1].strip() if "KONTEKS:" in system else ""
    if ctx and prompts.NO_CONTEXT not in ctx:
        return f"{prompts.FALLBACK_NO_MODEL}\n\nKonteks yang ditemukan untuk pertanyaan \"{user[:80]}\":\n{ctx[:600]}"
    return f"{prompts.FALLBACK_NO_MODEL}\n\nPesan Anda: {user[:200]}"
