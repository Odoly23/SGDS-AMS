"""
Model app `datasets`:
  Phrase      -> satu "konsep kalimat" (misal: "Selamat pagi"), kunci untuk semua bahasa
  Translation -> terjemahan konsep itu ke satu bahasa tertentu

Alur kualitas (crowdsourcing):
  draft (kontributor isi)  ->  review  ->  verified (reviewer/penutur asli setuju)
Hanya yang `verified` dipakai untuk training dan sebagai memori terjemahan.
"""
from django.conf import settings
from django.db import models

from chat.models import Language


class Phrase(models.Model):
    class Category(models.TextChoices):
        GREETING = "greeting", "Sapaan"
        MARKET = "market", "Pasar"
        FAMILY = "family", "Keluarga"
        SCHOOL = "school", "Sekolah"
        HEALTH = "health", "Kesehatan"
        CULTURE = "culture", "Budaya / adat"
        LAW = "law", "Hukum"
        OTHER = "other", "Lainnya"

    code = models.SlugField("Kode unik", max_length=40, unique=True, help_text="Contoh: greeting-001")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    context_note = models.CharField(
        "Catatan konteks", max_length=255, blank=True,
        help_text="Kapan kalimat ini dipakai? (sopan/akrab, pagi/sore, dll.)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "code"]
        verbose_name = "Kalimat (konsep)"
        verbose_name_plural = "Kalimat (konsep)"

    def __str__(self):
        return self.code


class Translation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft (belum dicek)"
        REVIEW = "review", "Menunggu review"
        VERIFIED = "verified", "Terverifikasi penutur asli"
        REJECTED = "rejected", "Ditolak"

    phrase = models.ForeignKey(Phrase, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.PROTECT, related_name="translations")
    text = models.TextField("Teks")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    dialect = models.CharField("Dialek / daerah", max_length=80, blank=True, help_text="Contoh: Mambae Ainaro")
    source = models.CharField("Sumber", max_length=120, blank=True, help_text="Contoh: seed-ai-draft, komunitas, buku X")
    notes = models.TextField("Catatan", blank=True)
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="contributed_translations",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_translations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # satu konsep boleh punya >1 terjemahan per bahasa (dialek berbeda), maka tidak unique
        ordering = ["phrase__category", "phrase__code", "language__sort_order"]
        permissions = [("verify_translation", "Boleh memverifikasi terjemahan")]
        verbose_name = "Terjemahan"
        verbose_name_plural = "Terjemahan"

    def __str__(self):
        return f"[{self.language.code}] {self.text[:40]}"
