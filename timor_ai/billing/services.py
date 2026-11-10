"""
Logika poin. Semua perubahan saldo lewat fungsi di sini (atomik, tercatat di buku besar).

Rumus biaya satu jawaban AI:
    biaya_usd   = (token_masuk * harga_in + token_keluar * harga_out) / 1.000.000
    biaya_poin  = ceil(biaya_usd * MARGIN * POINTS_PER_USD)     (minimal MIN_CHARGE)
Semua angka ada di settings.BILLING (diatur lewat .env).
"""
import hashlib
import math
import re
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import CreditTransaction, Package, Voucher, Wallet

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # tanpa 0/O/1/I agar mudah dibaca & diketik di HP
FAIL_LIMIT, FAIL_WINDOW = 5, 15 * 60            # 5 salah ketik per 15 menit -> terkunci sementara


class BillingError(Exception):
    """Pesan error aman ditampilkan ke user."""


# ----------------------------------------------------------------- dompet
def get_wallet(user) -> Wallet:
    """Ambil dompet; user baru otomatis dapat poin percobaan (sekali)."""
    wallet, created = Wallet.objects.get_or_create(user=user)
    if created and settings.BILLING["TRIAL_CREDITS"] > 0:
        _apply(wallet.pk, settings.BILLING["TRIAL_CREDITS"], CreditTransaction.Kind.TRIAL, "Poin percobaan")
        wallet.refresh_from_db()
    return wallet


def _apply(wallet_id, amount, kind, note="", **extra) -> int:
    """Ubah saldo secara atomik dan catat. Return saldo baru."""
    with transaction.atomic():
        w = Wallet.objects.select_for_update().get(pk=wallet_id)
        w.balance += amount
        w.save(update_fields=["balance", "updated_at"])
        CreditTransaction.objects.create(wallet=w, kind=kind, amount=amount, balance_after=w.balance, note=note, **extra)
        return w.balance


def add_credits_manual(user, amount: int, note: str = "") -> int:
    return _apply(get_wallet(user).pk, amount, CreditTransaction.Kind.MANUAL, note or "Penyesuaian admin")


def can_chat(user) -> bool:
    return get_wallet(user).balance >= settings.BILLING["MIN_BALANCE_TO_CHAT"]


# ------------------------------------------------------------------ biaya
def cost_in_credits(input_tokens: int, output_tokens: int) -> int:
    b = settings.BILLING
    usd = (input_tokens * b["PRICE_IN_PER_M"] + output_tokens * b["PRICE_OUT_PER_M"]) / 1_000_000
    return max(b["MIN_CHARGE"], math.ceil(usd * b["MARGIN"] * b["POINTS_PER_USD"]))


def charge_usage(user, input_tokens: int, output_tokens: int, note: str = "") -> tuple[int, int]:
    """Potong poin sesuai pemakaian token. Tidak pernah membuat saldo minus. Return (dipotong, saldo)."""
    wallet = get_wallet(user)
    cost = cost_in_credits(input_tokens, output_tokens)
    with transaction.atomic():
        w = Wallet.objects.select_for_update().get(pk=wallet.pk)
        cost = min(cost, max(w.balance, 0))
        balance = _apply(w.pk, -cost, CreditTransaction.Kind.USAGE, note, input_tokens=input_tokens, output_tokens=output_tokens)
    return cost, balance


# ---------------------------------------------------------------- voucher
def normalize_code(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


def hash_code(code: str) -> str:
    # SECRET_KEY ikut di-hash: hash curian dari DB tidak bisa dipakai untuk menebak kode offline
    return hashlib.sha256((settings.SECRET_KEY + normalize_code(code)).encode()).hexdigest()


def generate_vouchers(package: Package, count: int, batch: str = "", expires_at=None) -> list[str]:
    """Buat `count` voucher. Return daftar kode polos (format XXXX-XXXX-XXXX). Simpan sekali ini saja!"""
    codes = []
    with transaction.atomic():
        while len(codes) < count:
            raw = "".join(secrets.choice(ALPHABET) for _ in range(12))
            h = hash_code(raw)
            if Voucher.objects.filter(code_hash=h).exists():
                continue
            Voucher.objects.create(code_hash=h, code_hint=raw[-4:], package=package, batch=batch, expires_at=expires_at)
            codes.append(f"{raw[:4]}-{raw[4:8]}-{raw[8:]}")
    return codes


def redeem_voucher(user, code: str) -> dict:
    """Tukar kode voucher jadi poin. Pesan error sengaja seragam supaya kode tidak bisa ditebak-tebak."""
    key = f"voucher-fail:{user.pk}"
    if cache.get(key, 0) >= FAIL_LIMIT:
        raise BillingError("Terlalu banyak percobaan salah. Coba lagi dalam 15 menit.")
    generic = BillingError("Kode voucher tidak valid atau sudah dipakai.")
    norm = normalize_code(code)
    if len(norm) != 12:
        cache.set(key, cache.get(key, 0) + 1, FAIL_WINDOW)
        raise generic
    with transaction.atomic():
        v = Voucher.objects.select_for_update().select_related("package").filter(code_hash=hash_code(norm)).first()
        invalid = (
            v is None or v.status != Voucher.Status.UNUSED
            or (v.expires_at and v.expires_at < timezone.now())
        )
        if invalid:
            cache.set(key, cache.get(key, 0) + 1, FAIL_WINDOW)
            raise generic
        v.status, v.used_by, v.used_at = Voucher.Status.USED, user, timezone.now()
        v.save(update_fields=["status", "used_by", "used_at"])
        balance = _apply(get_wallet(user).pk, v.package.credits, CreditTransaction.Kind.VOUCHER,
                         f"Voucher …{v.code_hint} ({v.package.name})")
    cache.delete(key)
    return {"added": v.package.credits, "balance": balance, "package": v.package.name}
