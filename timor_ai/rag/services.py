"""
Layanan RAG (Retrieval Augmented Generation).

Alur:
  1. Admin upload PDF/TXT           -> extract_text()
  2. Teks dipotong kecil-kecil      -> chunk_text()
  3. Tiap potongan jadi vektor      -> embed_texts()
  4. Saat user bertanya, pertanyaan -> vektor, lalu dicari potongan paling mirip -> search()
  5. Potongan itu disisipkan ke prompt LLM supaya jawabannya berdasar dokumen.
"""
import hashlib
import logging
import math
import re
import threading

import numpy as np
from django.conf import settings

from .models import Chunk, Document

logger = logging.getLogger(__name__)
_st_model = None
_st_lock = threading.Lock()


# ---------------------------------------------------------------- ekstrak teks
def extract_text(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    # TXT: coba UTF-8 dulu, lalu Latin-1 (sering dipakai dokumen Portugis lama)
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


# ------------------------------------------------------------------ chunking
def chunk_text(text: str, size: int = None, overlap: int = None) -> list[str]:
    """Potong teks per paragraf, gabungkan sampai ~`size` karakter, dengan overlap."""
    cfg = settings.LAFEX_AI
    size = size or cfg["CHUNK_SIZE"]
    overlap = overlap if overlap is not None else cfg["CHUNK_OVERLAP"]
    text = re.sub(r"[ \t]+", " ", text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        # paragraf terlalu panjang -> belah per kalimat
        pieces = [para] if len(para) <= size else re.split(r"(?<=[.!?])\s+", para)
        for piece in pieces:
            while len(piece) > size:  # kalimat super panjang -> potong paksa
                chunks.append(piece[:size])
                piece = piece[size - overlap:]
            if len(current) + len(piece) + 1 <= size:
                current = f"{current} {piece}".strip()
            else:
                if current:
                    chunks.append(current)
                tail = current[-overlap:] if overlap and current else ""
                current = f"{tail} {piece}".strip()
    if current:
        chunks.append(current)
    return [c for c in chunks if len(c) > 20]


# ------------------------------------------------------------------ embedding
def backend_name() -> str:
    cfg = settings.LAFEX_AI
    if cfg["EMBEDDING_BACKEND"] == "hash":
        return "hash-256"
    return cfg["EMBEDDING_MODEL_ID"]


def _hash_embed(text: str, dim: int = 256) -> list[float]:
    """Embedding 'darurat' tanpa model: hashing kata. Cukup untuk tes alur, KUALITAS RENDAH."""
    vec = np.zeros(dim, dtype=np.float32)
    for tok in re.findall(r"\w+", text.lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0 if (h >> 8) % 2 else -1.0
    n = np.linalg.norm(vec)
    return (vec / n).tolist() if n else vec.tolist()


def _get_st_model():
    global _st_model
    with _st_lock:
        if _st_model is None:
            from sentence_transformers import SentenceTransformer

            _st_model = SentenceTransformer(settings.LAFEX_AI["EMBEDDING_MODEL_ID"])
        return _st_model


def embed_texts(texts: list[str], is_query: bool = False) -> list[list[float]]:
    cfg = settings.LAFEX_AI
    if cfg["EMBEDDING_BACKEND"] == "hash":
        return [_hash_embed(t) for t in texts]
    model = _get_st_model()
    # Model E5 butuh awalan "query: " / "passage: "
    prefix = "query: " if is_query else "passage: "
    if "e5" in cfg["EMBEDDING_MODEL_ID"].lower():
        texts = [prefix + t for t in texts]
    return model.encode(texts, normalize_embeddings=True).tolist()


# ------------------------------------------------------------------- proses
def process_document(doc: Document) -> int:
    """Ekstrak -> potong -> embed -> simpan. Return jumlah chunk."""
    try:
        text = extract_text(doc.file.path)
        pieces = chunk_text(text)
        if not pieces:
            raise ValueError("Tidak ada teks yang bisa diekstrak (PDF hasil scan? Perlu OCR).")
        vectors = embed_texts(pieces)
        doc.chunks.all().delete()
        Chunk.objects.bulk_create(
            [
                Chunk(document=doc, index=i, text=t, embedding=v, embedding_backend=backend_name())
                for i, (t, v) in enumerate(zip(pieces, vectors))
            ]
        )
        doc.status, doc.error = Document.Status.DONE, ""
        doc.save(update_fields=["status", "error"])
        return len(pieces)
    except Exception as exc:  # noqa: BLE001 - kita mau tampilkan pesan apa pun ke admin
        logger.exception("Gagal memproses dokumen %s", doc.pk)
        doc.status, doc.error = Document.Status.FAILED, str(exc)
        doc.save(update_fields=["status", "error"])
        return 0


# --------------------------------------------------------------------- cari
def search(query: str, top_k: int = None, min_score: float = None) -> list[dict]:
    """Cari potongan dokumen paling mirip dengan `query` (cosine similarity)."""
    cfg = settings.LAFEX_AI
    top_k = top_k or cfg["RAG_TOP_K"]
    min_score = cfg["RAG_MIN_SCORE"] if min_score is None else min_score

    rows = list(
        Chunk.objects.filter(embedding_backend=backend_name()).values_list("id", "embedding")
    )
    if not rows:
        return []
    ids = [r[0] for r in rows]
    matrix = np.array([r[1] for r in rows], dtype=np.float32)
    q = np.array(embed_texts([query], is_query=True)[0], dtype=np.float32)
    # vektor sudah dinormalisasi -> dot product = cosine similarity
    scores = matrix @ q
    order = np.argsort(-scores)[:top_k]
    best = [(ids[i], float(scores[i])) for i in order if scores[i] >= min_score and not math.isnan(scores[i])]
    if not best:
        return []
    chunks = Chunk.objects.select_related("document").in_bulk([b[0] for b in best])
    results = []
    for cid, score in best:
        c = chunks[cid]
        results.append(
            {
                "chunk_id": cid,
                "score": round(score, 3),
                "text": c.text,
                "document_id": c.document_id,
                "title": c.document.title,
                "category": c.document.category,
            }
        )
    return results
