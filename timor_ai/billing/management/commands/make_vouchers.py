"""
Membuat voucher isi ulang (seperti kartu pulsa) untuk dijual lewat agen/kios/WhatsApp.

  python manage.py make_vouchers --package 1 --count 50 --batch kios-dili --out voucher-kios-dili.csv

Kode polos hanya ada di file CSV hasilnya. SIMPAN file itu dengan aman (jangan di-commit ke Git,
jangan dibagikan ke grup umum). Database hanya menyimpan hash-nya.
"""
import csv
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from billing.models import Package
from billing.services import generate_vouchers


class Command(BaseCommand):
    help = "Buat voucher isi ulang dan tulis ke CSV."

    def add_arguments(self, parser):
        parser.add_argument("--package", type=int, required=True, help="ID paket (lihat Admin > Paket)")
        parser.add_argument("--count", type=int, required=True)
        parser.add_argument("--batch", default="")
        parser.add_argument("--days", type=int, default=0, help="Masa berlaku dalam hari (0 = tidak kedaluwarsa)")
        parser.add_argument("--out", required=True)

    def handle(self, *args, **o):
        pkg = Package.objects.filter(pk=o["package"]).first()
        if not pkg:
            raise CommandError("Paket tidak ditemukan.")
        if not 1 <= o["count"] <= 5000:
            raise CommandError("--count harus 1..5000")
        exp = timezone.now() + timedelta(days=o["days"]) if o["days"] else None
        codes = generate_vouchers(pkg, o["count"], o["batch"], exp)
        with open(o["out"], "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["kode", "paket", "poin", "harga_usd", "batch", "kedaluwarsa"])
            for c in codes:
                w.writerow([c, pkg.name, pkg.credits, pkg.price_usd, o["batch"], exp.date() if exp else ""])
        self.stdout.write(self.style.SUCCESS(f"{len(codes)} voucher ditulis ke {o['out']}. Simpan file ini dengan aman!"))
