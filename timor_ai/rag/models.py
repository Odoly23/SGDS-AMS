"""
Model app `rag`:
  Document -> file PDF/TXT yang diunggah admin (sejarah, budaya, hukum, adat)
  Chunk    -> potongan kecil teks dari dokumen + vektor embedding-nya

Vektor disimpan sebagai JSON (list angka) supaya jalan di PostgreSQL biasa
tanpa ekstensi tambahan. Kalau data sudah besar (>50 ribu potongan), pindah ke
pgvector (lihat README bagian "Upgrade ke pgvector").
"""
from django.conf import settings
from django.db import models

from chat.models import Language


class Document(models.Model):
    class Category(models.TextChoices):
        HISTORY = "history", "Sejarah"
        CULTURE = "culture", "Budaya"
        LAW = "law", "Hukum"
        ADAT = "adat", "Adat / Lisan"
        HEALTH = "health", "Kesehatan"
        OTHER = "other", "Lainnya"

    class Status(models.TextChoices):
        PENDING = "pending", "Belum diproses"
        DONE = "done", "Sudah diindeks"
        FAILED = "failed", "Gagal"

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=10, choices=Category.choices, default=Category.OTHER)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, blank=True, help_text="Bahasa isi dokumen")
    file = models.FileField(upload_to="rag_docs/", help_text="PDF atau TXT")
    source_note = models.CharField(
        "Sumber / lisensi", max_length=255, blank=True,
        help_text="Asal dokumen & izin pemakaian (penting untuk hak cipta!)",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Dokumen RAG"
        verbose_name_plural = "Dokumen RAG"

    def __str__(self):
        return self.title


class Chunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    index = models.PositiveIntegerField()
    text = models.TextField()
    embedding = models.JSONField(default=list)
    embedding_backend = models.CharField(max_length=120, blank=True, help_text="Nama model embedding yang membuat vektor ini")

    class Meta:
        ordering = ["document_id", "index"]

    def __str__(self):
        return f"{self.document_id}#{self.index}"
