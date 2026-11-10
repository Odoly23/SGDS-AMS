import csv

from django.contrib import admin, messages
from django.http import HttpResponse

from . import services
from .models import CreditTransaction, Package, Voucher, Wallet


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("name", "price_usd", "credits", "is_active", "sort_order")
    list_editable = ("price_usd", "credits", "is_active", "sort_order")


@admin.action(description="Batalkan voucher terpilih (void)")
def void_vouchers(modeladmin, request, queryset):
    n = queryset.filter(status=Voucher.Status.UNUSED).update(status=Voucher.Status.VOID)
    modeladmin.message_user(request, f"{n} voucher dibatalkan.", messages.SUCCESS)


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    """Voucher dibuat lewat perintah:  python manage.py make_vouchers --package 1 --count 50 --batch kios-dili"""
    list_display = ("code_hint", "package", "batch", "status", "used_by", "used_at", "expires_at", "created_at")
    list_filter = ("status", "package", "batch")
    search_fields = ("code_hint", "batch", "used_by__email")
    readonly_fields = ("code_hash", "code_hint", "package", "used_by", "used_at", "created_at")
    actions = [void_vouchers]

    def has_add_permission(self, request):
        return False  # kode polos hanya bisa dibuat lewat make_vouchers (supaya CSV-nya ikut keluar)


class TxInline(admin.TabularInline):
    model = CreditTransaction
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in CreditTransaction._meta.fields if f.name != "wallet"]
    ordering = ["-created_at"]
    max_num = 0

    def has_add_permission(self, request, obj=None):
        return False


@admin.action(description="Tambah 100 poin (manual)")
def add_100(modeladmin, request, queryset):
    for w in queryset:
        services.add_credits_manual(w.user, 100, f"Ditambah oleh {request.user}")
    modeladmin.message_user(request, "100 poin ditambahkan.", messages.SUCCESS)


@admin.action(description="Tambah 1.000 poin (manual)")
def add_1000(modeladmin, request, queryset):
    for w in queryset:
        services.add_credits_manual(w.user, 1000, f"Ditambah oleh {request.user}")
    modeladmin.message_user(request, "1.000 poin ditambahkan.", messages.SUCCESS)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "updated_at")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("user", "balance", "updated_at")   # saldo hanya berubah lewat transaksi
    inlines = [TxInline]
    actions = [add_100, add_1000]

    def has_add_permission(self, request):
        return False


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "wallet", "kind", "amount", "balance_after", "input_tokens", "output_tokens", "note")
    list_filter = ("kind", "created_at")
    search_fields = ("wallet__user__email", "note")
    readonly_fields = [f.name for f in CreditTransaction._meta.fields]
    actions = ["export_csv"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.action(description="Export CSV (laporan)")
    def export_csv(self, request, queryset):
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="transaksi.csv"'
        resp.write("﻿")
        w = csv.writer(resp)
        w.writerow(["waktu", "user", "jenis", "poin", "saldo_setelah", "token_masuk", "token_keluar", "catatan"])
        for t in queryset.select_related("wallet__user"):
            w.writerow([t.created_at.isoformat(), t.wallet.user, t.kind, t.amount, t.balance_after,
                        t.input_tokens or "", t.output_tokens or "", t.note])
        return resp
