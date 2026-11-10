"""
Model app `billing`: sistem poin prabayar ala pulsa.

  Package            -> paket yang Anda jual (mis. "Paket 1 USD = 1.000 poin")
  Voucher            -> kode isi ulang sekali pakai (dijual lewat agen/kios/WhatsApp)
  Wallet             -> saldo poin tiap user
  CreditTransaction  -> buku besar: setiap perubahan saldo tercatat (tidak pernah dihapus)

Kode voucher TIDAK disimpan polos, hanya hash-nya. Jadi kalau database bocor, kode yang
belum terpakai tidak ikut bocor. Kode asli hanya terlihat sekali saat dibuat (file CSV).
"""
from django.conf import settings
from django.db import models


class Package(models.Model):
    name = models.CharField("Nama paket", max_length=80)
    description = models.CharField(max_length=200, blank=True)
    price_usd = models.DecimalField("Harga (USD)", max_digits=8, decimal_places=2,
                                    help_text="Timor-Leste memakai dolar AS")
    credits = models.PositiveIntegerField("Jumlah poin")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["sort_order", "price_usd"]
        verbose_name = "Paket"
        verbose_name_plural = "Paket"

    def __str__(self):
        return f"{self.name} (${self.price_usd} = {self.credits} poin)"


class Voucher(models.Model):
    class Status(models.TextChoices):
        UNUSED = "unused", "Belum dipakai"
        USED = "used", "Sudah dipakai"
        VOID = "void", "Dibatalkan"

    code_hash = models.CharField(max_length=64, unique=True, editable=False)
    code_hint = models.CharField("4 karakter terakhir", max_length=4, editable=False)
    package = models.ForeignKey(Package, on_delete=models.PROTECT, related_name="vouchers")
    batch = models.CharField("Batch / agen", max_length=80, blank=True, help_text="Mis. kios-dili-01, untuk melacak penjualan")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNUSED)
    expires_at = models.DateTimeField("Kedaluwarsa", null=True, blank=True)
    used_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Voucher"
        verbose_name_plural = "Voucher"

    def __str__(self):
        return f"…{self.code_hint} ({self.package.name}, {self.get_status_display()})"


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.IntegerField("Saldo poin", default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dompet"
        verbose_name_plural = "Dompet"

    def __str__(self):
        return f"{self.user} = {self.balance} poin"


class CreditTransaction(models.Model):
    class Kind(models.TextChoices):
        TRIAL = "trial", "Poin gratis (percobaan)"
        VOUCHER = "voucher", "Isi ulang voucher"
        MANUAL = "manual", "Penyesuaian admin"
        USAGE = "usage", "Pemakaian chat"
        REWARD = "reward", "Hadiah kontribusi bahasa"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    amount = models.IntegerField(help_text="Positif = masuk, negatif = terpakai")
    balance_after = models.IntegerField()
    note = models.CharField(max_length=200, blank=True)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Transaksi poin"
        verbose_name_plural = "Transaksi poin"

    def __str__(self):
        return f"{self.wallet.user} {self.amount:+d} ({self.kind})"
