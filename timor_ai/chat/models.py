"""
Model app `chat`:
  Language     -> daftar bahasa yang didukung
  Conversation -> satu sesi percakapan milik satu user
  Message      -> satu pesan (dari user atau dari AI) di dalam percakapan
"""
from django.conf import settings
from django.db import models


class Language(models.Model):
    class Kind(models.TextChoices):
        OFFICIAL = "official", "Bahasa resmi"
        WORKING = "working", "Bahasa kerja"
        NATIONAL = "national", "Bahasa nasional / lokal"
        VARIETY = "variety", "Varian dari bahasa lain"

    class Verification(models.TextChoices):
        OK = "ok", "Nama sudah umum"
        VERIFY = "verify", "Perlu diverifikasi"

    code = models.SlugField("Kode", max_length=30, unique=True, help_text="Contoh: tet, por, mambae")
    name = models.CharField("Nama (Indonesia)", max_length=80)
    native_name = models.CharField("Nama asli", max_length=80, blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.NATIONAL)
    iso_639_3 = models.CharField("Kode ISO 639-3", max_length=3, blank=True)
    verification = models.CharField(max_length=10, choices=Verification.choices, default=Verification.OK)
    notes = models.TextField("Catatan linguistik", blank=True)
    is_active = models.BooleanField("Tampilkan di pilihan user", default=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Bahasa"
        verbose_name_plural = "Bahasa"

    def __str__(self):
        return self.name

    @property
    def is_local(self):
        return self.kind in (self.Kind.NATIONAL, self.Kind.VARIETY)


class Conversation(models.Model):
    class Mode(models.TextChoices):
        CHAT = "chat", "Tanya jawab (RAG)"
        TRANSLATE = "translate", "Terjemahan"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=200, blank=True)
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.CHAT)
    # bahasa jawaban AI (mode chat) atau bahasa tujuan (mode translate)
    language = models.ForeignKey(Language, on_delete=models.PROTECT, related_name="+")
    source_language = models.ForeignKey(
        Language, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="Hanya untuk mode terjemahan. Kosong = deteksi otomatis.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"#{self.pk} {self.title or 'Tanpa judul'} ({self.user})"


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "AI"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    detected_language = models.CharField(max_length=30, blank=True, help_text="Hasil auto-detect (kode bahasa)")
    sources = models.JSONField("Sumber RAG", default=list, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    credits_charged = models.PositiveIntegerField(null=True, blank=True, help_text="Poin yang dipotong dari user untuk jawaban ini")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
