"""
Mengisi database awal:
  1. Tabel Language dari chat/language_registry.py
  2. Phrase + Translation dari seed_data.json (atau file CSV hasil crowdsourcing)

Pemakaian:
  python manage.py seed_phrases                       # pakai seed_data.json bawaan
  python manage.py seed_phrases --file data_baru.csv  # impor CSV (kolom: code,category,tet,por,eng,mambae,...)
Aman dijalankan berulang kali (tidak membuat data ganda).
"""
import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from chat.language_registry import LANGUAGES
from chat.models import Language
from datasets.models import Phrase, Translation

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "seed" / "seed_data.json"
MAIN_ORDER = {"tet": 1, "por": 2, "eng": 3, "ind": 4}


def seed_languages():
    for i, (code, name, native, kind, iso, status, notes) in enumerate(LANGUAGES):
        Language.objects.update_or_create(
            code=code,
            defaults=dict(
                name=name, native_name=native, kind=kind, iso_639_3=iso, verification=status, notes=notes,
                sort_order=MAIN_ORDER.get(code, 100 + i),
            ),
        )


def read_rows(path: Path):
    """Return iterator of (code, category, {lang_code: text}) dari JSON atau CSV."""
    if path.suffix.lower() == ".json":
        doc = json.loads(path.read_text(encoding="utf-8"))
        for p in doc["phrases"]:
            yield p["code"], p["category"], p["translations"]
    elif path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                langs = {k: v for k, v in row.items() if k not in ("code", "category") and k}
                yield row["code"], row["category"] or "other", langs
    else:
        raise CommandError("Format file harus .json atau .csv")


class Command(BaseCommand):
    help = "Isi tabel Language dan impor dataset kalimat (JSON/CSV)."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DEFAULT_FILE))
        parser.add_argument("--status", default="draft", choices=["draft", "review"],
                            help="Status awal terjemahan yang diimpor (verified hanya lewat reviewer di Admin)")
        parser.add_argument("--source", default="seed-ai-draft")

    def handle(self, *args, **opts):
        seed_languages()
        self.stdout.write(self.style.SUCCESS(f"Bahasa: {Language.objects.count()} entri"))
        path = Path(opts["file"])
        if not path.exists():
            raise CommandError(f"File tidak ditemukan: {path}")

        langs = {l.code: l for l in Language.objects.all()}
        created = skipped = unknown = 0
        for code, category, trans in read_rows(path):
            phrase, _ = Phrase.objects.get_or_create(code=code, defaults={"category": category})
            for lang_code, text in trans.items():
                text = (text or "").strip()
                if not text:
                    continue  # sel kosong = menunggu diisi komunitas
                lang = langs.get(lang_code)
                if not lang:
                    unknown += 1
                    continue
                _, was_created = Translation.objects.get_or_create(
                    phrase=phrase, language=lang, text=text,
                    defaults={"status": opts["status"], "source": opts["source"]},
                )
                created += was_created
                skipped += not was_created
        self.stdout.write(self.style.SUCCESS(
            f"Phrase: {Phrase.objects.count()} | Terjemahan baru: {created} | sudah ada: {skipped} | kode bahasa tak dikenal: {unknown}"
        ))
