"""
Logika inti chat. View (views.py) tipis; semua kerja berat ada di sini.

  reply_chat()      -> mode tanya jawab dengan RAG
  reply_translate() -> mode terjemahan (memori terjemahan -> few-shot -> LLM)
"""
import re
import time

from datasets.models import Translation
from rag.services import search as rag_search

from . import llm, prompts
from .detect import detect_language
from .models import Conversation, Language, Message

HISTORY_TURNS = 6  # berapa pesan terakhir yang diikutkan ke model


def _norm(text: str) -> str:
    return re.sub(r"[^\w' ]+", "", text.lower().replace("’", "'")).strip()


def _words(text: str) -> set[str]:
    return set(re.findall(r"[\w']+", text.lower()))


# ------------------------------------------------------------------ MODE CHAT
def reply_chat(conv: Conversation, user_text: str) -> Message:
    started = time.monotonic()
    lang = conv.language

    detected = detect_language(user_text) or ""
    sources = rag_search(user_text)
    context = "\n\n".join(f"[{i + 1}] ({s['title']}) {s['text']}" for i, s in enumerate(sources)) or prompts.NO_CONTEXT

    system = prompts.SYSTEM_CHAT.format(
        language_name=lang.name,
        context=context,
        local_language_warning=prompts.LOCAL_LANGUAGE_WARNING.format(language_name=lang.name) if lang.is_local else "",
    )
    messages = [{"role": "system", "content": system}]
    history = list(conv.messages.order_by("-created_at", "-id")[:HISTORY_TURNS])[::-1]
    messages += [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": user_text})

    answer = llm.generate(messages)

    Message.objects.create(conversation=conv, role=Message.Role.USER, content=user_text, detected_language=detected)
    return Message.objects.create(
        conversation=conv,
        role=Message.Role.ASSISTANT,
        content=answer,
        detected_language=lang.code,
        sources=[{k: s[k] for k in ("title", "score", "category", "document_id")} for s in sources],
        model_name=llm.model_name(),
        latency_ms=int((time.monotonic() - started) * 1000),
    )


# ------------------------------------------------------------- MODE TERJEMAHAN
def _memory_lookup(text: str, src: Language | None, tgt: Language):
    """Cari kalimat yang SAMA PERSIS di database. Ini menghindari halusinasi untuk kalimat yang sudah ada."""
    if src is None:
        return None
    norm = _norm(text)
    candidates = Translation.objects.filter(language=src).exclude(status=Translation.Status.REJECTED).select_related("phrase")
    for cand in candidates.iterator():
        if _norm(cand.text) == norm:
            hit = (
                Translation.objects.filter(phrase=cand.phrase, language=tgt)
                .exclude(status=Translation.Status.REJECTED)
                .order_by("-status")  # 'verified' > 'review' > 'draft' secara alfabet terbalik
                .first()
            )
            if hit:
                return hit
    return None


def _few_shot_examples(text: str, src: Language | None, tgt: Language, k: int = 5) -> str:
    """Ambil contoh pasangan (src -> tgt) yang kata-katanya mirip, untuk dipakai sebagai contoh di prompt."""
    if src is None:
        return ""
    words = _words(text)
    src_rows = (
        Translation.objects.filter(language=src).exclude(status=Translation.Status.REJECTED)
        .select_related("phrase")[:1000]
    )
    scored = []
    for s in src_rows:
        overlap = len(words & _words(s.text))
        if overlap:
            scored.append((overlap, s))
    scored.sort(key=lambda x: -x[0])
    lines = []
    for _, s in scored:
        t = Translation.objects.filter(phrase=s.phrase, language=tgt).exclude(status=Translation.Status.REJECTED).first()
        if t:
            lines.append(f"{src.name}: {s.text}\n{tgt.name}: {t.text}")
        if len(lines) >= k:
            break
    return prompts.EXAMPLES_HEADER + "\n\n".join(lines) + "\n" if lines else ""


def reply_translate(conv: Conversation, user_text: str) -> Message:
    started = time.monotonic()
    tgt = conv.language
    src = conv.source_language
    detected = detect_language(user_text) or ""
    if src is None and detected:
        src = Language.objects.filter(code=detected).first()

    Message.objects.create(conversation=conv, role=Message.Role.USER, content=user_text, detected_language=detected)

    hit = _memory_lookup(user_text, src, tgt)
    if hit:
        note = "" if hit.status == Translation.Status.VERIFIED else "\n\n(Catatan: terjemahan ini dari database tapi belum diverifikasi penutur asli.)"
        return Message.objects.create(
            conversation=conv, role=Message.Role.ASSISTANT, content=hit.text + note,
            detected_language=tgt.code, sources=[{"title": "Memori terjemahan", "id": hit.pk, "status": hit.status}],
            model_name="translation-memory", latency_ms=int((time.monotonic() - started) * 1000),
        )

    system = prompts.SYSTEM_TRANSLATE.format(
        src=src.name if src else "bahasa asal (deteksi sendiri)",
        tgt=tgt.name,
        examples=_few_shot_examples(user_text, src, tgt),
    )
    answer = llm.generate([{"role": "system", "content": system}, {"role": "user", "content": user_text}], max_new_tokens=200)
    warning = ""
    if tgt.is_local:
        warning = f"\n\n(Perhatian: terjemahan ke {tgt.name} masih eksperimental. Mohon dicek penutur asli.)"
    return Message.objects.create(
        conversation=conv, role=Message.Role.ASSISTANT, content=answer + warning, detected_language=tgt.code,
        model_name=llm.model_name(), latency_ms=int((time.monotonic() - started) * 1000),
    )
