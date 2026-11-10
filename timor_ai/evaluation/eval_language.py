"""
Evaluasi sederhana: apakah model menjawab dalam bahasa yang dipilih user?

Jalankan dari folder timor_ai/:
  python evaluation/eval_language.py                # semua bahasa utama
  python evaluation/eval_language.py --langs tet por eng

Cara menilai:
  - tet/por/eng/ind : jawaban dideteksi otomatis (chat/detect.py) lalu dibandingkan dengan bahasa target.
  - bahasa lokal    : belum bisa dideteksi otomatis -> hanya dicek "tidak kosong" dan "bukan bahasa Inggris",
                      lalu jawaban ditulis ke CSV untuk dinilai MANUAL oleh penutur asli.
Hasil: ringkasan di terminal + evaluation/results.csv

Catatan: dengan LLM_BACKEND=dummy skor bahasa akan rendah (jawaban demo berbahasa Indonesia) -> itu normal.
"""
import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from chat import llm, prompts  # noqa: E402
from chat.detect import detect_language  # noqa: E402
from chat.models import Conversation, Language  # noqa: E402
from chat.services import reply_chat  # noqa: E402

QUESTIONS = [
    "Apa itu tais dan kenapa penting bagi budaya Timor-Leste?",
    "Kapan Timor-Leste merdeka?",
    "Bagaimana cara menyapa orang tua dengan sopan?",
    "Apa yang harus dilakukan jika anak demam tinggi?",
    "Sebutkan tiga makanan khas Timor-Leste.",
]
DETECTABLE = {"tet", "por", "eng", "ind"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="*", default=["tet", "por", "eng", "ind"])
    args = ap.parse_args()

    user, _ = get_user_model().objects.get_or_create(username="eval-bot")
    rows, summary = [], {}
    for code in args.langs:
        lang = Language.objects.filter(code=code).first()
        if not lang:
            print(f"[lewati] bahasa '{code}' belum ada. Jalankan: python manage.py seed_phrases")
            continue
        ok = 0
        for q in QUESTIONS:
            conv = Conversation.objects.create(user=user, title="[eval] " + q[:40], language=lang)
            answer = reply_chat(conv, q).content
            if code in DETECTABLE:
                # buang baris awalan mode-demo supaya tidak mengganggu deteksi
                body = answer.replace(prompts.FALLBACK_NO_MODEL, "")
                passed = detect_language(body) == code
            else:
                passed = bool(answer.strip()) and detect_language(answer) != "eng"
            ok += passed
            rows.append({"lang": code, "question": q, "answer": answer.replace("\n", " ")[:500], "auto_pass": passed, "manual_score_1_5": ""})
        summary[code] = ok

    out = ROOT / "evaluation" / "results.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["lang", "question", "answer", "auto_pass", "manual_score_1_5"])
        w.writeheader()
        w.writerows(rows)

    print(f"\nModel: {llm.model_name()}")
    print("=" * 40)
    for code, ok in summary.items():
        print(f"{code:12s} {ok}/{len(QUESTIONS)}  ({100 * ok // len(QUESTIONS)}%)")
    print("=" * 40)
    print(f"Detail: {out}  (isi kolom manual_score_1_5 untuk bahasa lokal)")


if __name__ == "__main__":
    main()
