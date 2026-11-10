"""
Ekspor terjemahan TERVERIFIKASI ke format JSONL untuk fine-tuning LoRA.

  python manage.py export_finetune --out training/train.jsonl

Setiap pasangan (A -> B) untuk semua kombinasi bahasa dari satu Phrase dibuat jadi satu contoh
instruksi. Contoh: "Terjemahkan dari Tetun ke Portugis: Bondia!" -> "Bom dia!"
Gunakan --include-draft HANYA untuk uji coba pipeline (kualitas data tidak terjamin).
"""
import itertools
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from datasets.models import Phrase, Translation


class Command(BaseCommand):
    help = "Ekspor dataset terjemahan ke JSONL untuk fine-tuning."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="training/train.jsonl")
        parser.add_argument("--include-draft", action="store_true")

    def handle(self, *args, **opts):
        ok = [Translation.Status.VERIFIED]
        if opts["include_draft"]:
            ok += [Translation.Status.DRAFT, Translation.Status.REVIEW]
        out = Path(opts["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        n = 0
        with open(out, "w", encoding="utf-8") as f:
            for phrase in Phrase.objects.prefetch_related("translations__language"):
                items = [t for t in phrase.translations.all() if t.status in ok]
                for a, b in itertools.permutations(items, 2):
                    if a.language_id == b.language_id:
                        continue
                    row = {
                        "instruction": f"Terjemahkan dari {a.language.name} ke {b.language.name}. Keluarkan hanya terjemahannya.",
                        "input": a.text,
                        "output": b.text,
                    }
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    n += 1
        self.stdout.write(self.style.SUCCESS(f"{n} contoh ditulis ke {out}"))
        if n == 0:
            self.stdout.write(self.style.WARNING("Kosong: belum ada terjemahan terverifikasi. Pakai --include-draft untuk uji coba."))
