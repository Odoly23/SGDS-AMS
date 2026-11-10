"""
Auto-detect bahasa dari teks user.

Kenyataan: library deteksi bahasa umum TIDAK mengenal Tetun (apalagi Mambae/Makasae).
Jadi kita pakai 2 lapis:
  1. Daftar kata khas Tetun (stopword) -> kalau skornya tinggi, jawab "tet".
  2. langdetect untuk Portugis / Inggris / Indonesia.
Bahasa lokal lain TIDAK bisa dideteksi otomatis -> user pilih manual.
Kalau data Mambae/Makasae sudah banyak, ganti fungsi ini dengan classifier kecil
(mis. fastText) yang dilatih dari tabel Translation.
"""
import re

from .language_registry import LANGDETECT_MAP

# Kata sangat umum di Tetun (dan jarang di Portugis/Inggris/Indonesia)
TETUN_MARKERS = {
    "ha'u", "hau", "ita", "ami", "imi", "sira", "nia", "ne'e", "neʼe", "ne'ebé", "neebe",
    "iha", "ba", "husi", "ho", "no", "ka", "lae", "ona", "sei", "bele", "tenke", "hakarak",
    "hatene", "diak", "di'ak", "obrigadu", "obrigada", "bondia", "botarde", "bonoite",
    "saida", "oinsá", "oinsa", "bainhira", "hira", "mak", "maibé", "mais", "katak", "loron",
    "tebes", "barak", "oan", "uma", "ema", "ko'alia", "koalia", "favór", "favor", "deskulpa",
    "mai", "hela", "han", "hemu", "moras", "belun", "eskola", "hotu", "mós", "mos",
}
# Penanda yang bentrok dengan Portugis ("no", "mais", "favor", "ba"...) diberi bobot kecil
WEAK = {"no", "mais", "favor", "ho", "ka", "ba", "mai", "mak"}


def _tetun_score(text: str) -> float:
    words = re.findall(r"[\w'ʼ’]+", text.lower().replace("’", "'"))
    if not words:
        return 0.0
    score = 0.0
    for w in words:
        if w in TETUN_MARKERS:
            score += 0.4 if w in WEAK else 1.0
    return score / len(words)


def detect_language(text: str) -> str | None:
    """Return kode bahasa kita ("tet", "por", "eng", "ind") atau None jika tidak yakin."""
    text = (text or "").strip()
    if len(text) < 3:
        return None
    if _tetun_score(text) >= 0.25:
        return "tet"
    try:
        from langdetect import DetectorFactory, detect_langs

        DetectorFactory.seed = 0
        results = detect_langs(text)
    except Exception:  # noqa: BLE001 - library belum terpasang / teks aneh
        return None
    inverse = {v: k for k, v in LANGDETECT_MAP.items()}
    for r in results:
        if r.lang in inverse and r.prob >= 0.6:
            # Tetun sering salah terdeteksi sebagai Indonesia/Portugis; jika ada penanda Tetun, utamakan Tetun
            if _tetun_score(text) >= 0.12:
                return "tet"
            return inverse[r.lang]
    return "tet" if _tetun_score(text) >= 0.12 else None
