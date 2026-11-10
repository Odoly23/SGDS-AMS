"""
Admin untuk crowdsourcing data bahasa daerah.

Cara kerja:
- Kontributor (grup "Kontributor") hanya bisa menambah Terjemahan berstatus DRAFT/REVIEW.
- Reviewer (grup "Reviewer", punya izin `verify_translation`) boleh mengubah status jadi VERIFIED.
- Ada tombol aksi: "Tandai terverifikasi", "Tolak", dan "Export CSV".
"""
import csv

from django.contrib import admin, messages
from django.http import HttpResponse

from .models import Phrase, Translation


class TranslationInline(admin.TabularInline):
    model = Translation
    extra = 0
    fields = ("language", "text", "dialect", "status", "notes")
    readonly_fields = ()

    def get_readonly_fields(self, request, obj=None):
        # Non-reviewer tidak boleh mengubah status dari inline
        if not request.user.has_perm("datasets.verify_translation"):
            return ("status",)
        return ()


@admin.register(Phrase)
class PhraseAdmin(admin.ModelAdmin):
    list_display = ("code", "category", "context_note", "bahasa_terisi")
    list_filter = ("category",)
    search_fields = ("code", "translations__text")
    inlines = [TranslationInline]

    @admin.display(description="Bahasa terisi")
    def bahasa_terisi(self, obj):
        return ", ".join(sorted({t.language.code for t in obj.translations.all()}))

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, Translation):
                if not obj.pk:
                    obj.contributor = request.user  # catat siapa yang menambah
                    # Non-reviewer: status otomatis DRAFT (field status read-only untuk mereka)
            obj.save()
        formset.save_m2m()
        for obj in formset.deleted_objects:
            obj.delete()


@admin.action(description="Tandai terverifikasi (khusus reviewer)")
def mark_verified(modeladmin, request, queryset):
    if not request.user.has_perm("datasets.verify_translation"):
        modeladmin.message_user(request, "Anda tidak punya izin memverifikasi.", messages.ERROR)
        return
    n = queryset.update(status=Translation.Status.VERIFIED, reviewed_by=request.user)
    modeladmin.message_user(request, f"{n} terjemahan ditandai terverifikasi.", messages.SUCCESS)


@admin.action(description="Kirim ke review")
def mark_review(modeladmin, request, queryset):
    n = queryset.exclude(status=Translation.Status.VERIFIED).update(status=Translation.Status.REVIEW)
    modeladmin.message_user(request, f"{n} terjemahan dikirim ke review.", messages.SUCCESS)


@admin.action(description="Tolak (khusus reviewer)")
def mark_rejected(modeladmin, request, queryset):
    if not request.user.has_perm("datasets.verify_translation"):
        modeladmin.message_user(request, "Anda tidak punya izin.", messages.ERROR)
        return
    queryset.update(status=Translation.Status.REJECTED, reviewed_by=request.user)


@admin.action(description="Export terpilih ke CSV")
def export_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="translations.csv"'
    response.write("﻿")  # BOM supaya Excel membaca UTF-8 dengan benar
    w = csv.writer(response)
    w.writerow(["phrase_code", "category", "language", "text", "dialect", "status", "source"])
    for t in queryset.select_related("phrase", "language"):
        w.writerow([t.phrase.code, t.phrase.category, t.language.code, t.text, t.dialect, t.status, t.source])
    return response


@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    list_display = ("phrase", "language", "short_text", "status", "dialect", "contributor", "updated_at")
    list_filter = ("status", "language", "phrase__category")
    search_fields = ("text", "phrase__code")
    list_select_related = ("phrase", "language", "contributor")
    autocomplete_fields = ("phrase",)
    actions = [mark_review, mark_verified, mark_rejected, export_csv]
    readonly_fields = ("contributor", "reviewed_by")

    @admin.display(description="Teks")
    def short_text(self, obj):
        return obj.text[:60]

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if not request.user.has_perm("datasets.verify_translation"):
            base.append("status")
        return base

    def save_model(self, request, obj, form, change):
        if not change:
            obj.contributor = request.user
        if "status" in form.changed_data and obj.status == Translation.Status.VERIFIED:
            obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)
