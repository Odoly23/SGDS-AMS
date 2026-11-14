"""
Model Lian Timor.

  Pengguna       -> User (pakai email ATAU nomor HP, atau "tamu" tanpa daftar)
  Bahasa         -> 4 bahasa aplikasi + bahasa daerah untuk crowdsource
  Level          -> 5 level materi (Pasar, Sapa, Sekolah, Kerja, Perjalanan)
  Materi         -> kelompok kecil kalimat di dalam satu Level (mis. 4 materi x 5 kalimat = 20)
  Kalimat        -> satu kalimat dalam 4 bahasa + suara
  KarakterAI     -> 3 karakter AI (Preman / Sopan / Profesional), teksnya bisa diubah Admin
  RekamanSuara   -> suara dari crowdsource (bahasa daerah) untuk melatih AI
  ProgresBelajar -> kalimat mana yang sudah dipelajari user (untuk progress bar)

Teks yang tampil ke user disimpan dalam 4 kolom (_tet, _en, _pt, _id). Sederhana dan mudah
diisi lewat Admin. Bahasa daerah TIDAK disimpan sebagai kolom, melainkan lewat RekamanSuara.
"""
import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

UI_BAHASA = [("tet", "Tetun"), ("en", "English"), ("pt", "Português"), ("id", "Bahasa Indonesia")]
UI_KODE = [k for k, _ in UI_BAHASA]
BAHASA_DEFAULT = "tet"


def kode_acak():
    """Kode samaran 12 karakter untuk pengirim suara (bukan nama/HP/email)."""
    return secrets.token_hex(6)


def teks_bahasa(obj, awalan, bahasa):
    """Ambil obj.<awalan>_<bahasa>; jika kosong, jatuh ke Tetun lalu bahasa lain yang terisi."""
    for kode in (bahasa, BAHASA_DEFAULT, "en", "pt", "id"):
        nilai = getattr(obj, f"{awalan}_{kode}", "")
        if nilai:
            return nilai
    return ""


# ===================================================================== PENGGUNA
class Pengguna(AbstractUser):
    """
    User. `username` diisi otomatis dari email atau nomor HP (form daftar akan mengurusnya).
    Kita TIDAK memverifikasi nomor HP lewat SMS (butuh layanan berbayar); nomor HP hanya
    sebagai pengenal login bersama password.
    """

    class Peran(models.TextChoices):
        ANAK = "anak", "Anak sekolah"
        DEWASA = "dewasa", "Dewasa"
        GURU = "guru", "Guru"
        IBU_PASAR = "ibu_pasar", "Ibu di pasar"

    peran = models.CharField("Peran", max_length=12, choices=Peran.choices, blank=True,
                             help_text="Dijawab user setelah login: 'Kamu siapa?'. Dipakai untuk menyesuaikan materi.")
    bahasa_ui = models.CharField("Bahasa tampilan", max_length=3, choices=UI_BAHASA, default=BAHASA_DEFAULT)
    telepon = models.CharField("Nomor HP", max_length=20, unique=True, null=True, blank=True,
                               help_text="Format +670xxxxxxx. Kosong jika daftar dengan email.")
    is_tamu = models.BooleanField("Tamu (tanpa daftar)", default=False,
                                  help_text="Dibuat otomatis oleh tombol 'Lanjut tanpa daftar'. Progres tersimpan di akun tamu ini.")
    kode_anonim = models.CharField(
        max_length=12, unique=True, default=kode_acak, editable=False,
        help_text="Kode samaran. Dipakai di RekamanSuara agar Admin bisa memblokir pengirim nakal tanpa melihat identitasnya.",
    )

    class Meta:
        verbose_name = "Pengguna"
        verbose_name_plural = "Pengguna"

    def __str__(self):
        return self.email or self.telepon or self.username


# ======================================================================= BAHASA
class Bahasa(models.Model):
    class Jenis(models.TextChoices):
        UI = "ui", "Bahasa aplikasi"
        LOKAL = "lokal", "Bahasa daerah"

    kode = models.SlugField("Kode", max_length=30, unique=True, help_text="Contoh: tet, en, mambae")
    nama = models.CharField("Nama", max_length=80)
    nama_asli = models.CharField("Nama dalam bahasanya sendiri", max_length=80, blank=True)
    jenis = models.CharField(max_length=6, choices=Jenis.choices, default=Jenis.LOKAL)
    iso_639_3 = models.CharField("Kode ISO 639-3", max_length=3, blank=True)
    untuk_crowdsource = models.BooleanField("Tampil di halaman 'Bantu AI'", default=True)
    perlu_verifikasi = models.BooleanField(
        "Nama perlu diverifikasi", default=False,
        help_text="Centang jika belum pasti ini bahasa tersendiri (bukan dialek/nama desa). Cek ke INL-UNTL.")
    catatan = models.TextField("Catatan linguistik", blank=True)
    aktif = models.BooleanField(default=True)
    urutan = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["urutan", "nama"]
        verbose_name = "Bahasa"
        verbose_name_plural = "Bahasa"

    def __str__(self):
        return self.nama


# ================================================================= LEVEL & MATERI
class Warna(models.TextChoices):
    """Warna kartu (bendera & tais). Dipetakan ke kelas CSS di Tailwind."""
    MERAH = "merah", "Merah"
    KUNING = "kuning", "Kuning"
    HITAM = "hitam", "Hitam"
    PUTIH = "putih", "Putih"


class Level(models.Model):
    TARGET_KALIMAT = 20   # setiap Level sebaiknya berisi 20 kalimat

    nomor = models.PositiveSmallIntegerField(unique=True, help_text="1 sampai 5")
    judul_tet = models.CharField("Judul (Tetun)", max_length=80)
    judul_en = models.CharField("Judul (English)", max_length=80, blank=True)
    judul_pt = models.CharField("Judul (Português)", max_length=80, blank=True)
    judul_id = models.CharField("Judul (Indonesia)", max_length=80, blank=True)
    emoji = models.CharField("Gambar (emoji)", max_length=8, blank=True, help_text="Gambar besar di kartu, mis. 🥬")
    warna = models.CharField(max_length=6, choices=Warna.choices, default=Warna.MERAH)
    aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nomor"]
        verbose_name = "Level"
        verbose_name_plural = "Level"

    def __str__(self):
        return f"Level {self.nomor}: {self.judul_tet}"

    def judul(self, bahasa=BAHASA_DEFAULT):
        return teks_bahasa(self, "judul", bahasa)

    @property
    def total_kalimat(self):
        return Kalimat.objects.filter(materi__level=self, materi__aktif=True, aktif=True).count()

    def clean(self):
        if self.nomor and not 1 <= self.nomor <= 5:
            raise ValidationError({"nomor": "Nomor level harus 1 sampai 5."})


class Materi(models.Model):
    """Kelompok kecil kalimat di dalam satu Level (mis. 'Menawar harga'). Opsional tetapi memudahkan Admin."""
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="materi")
    urutan = models.PositiveSmallIntegerField(default=1)
    judul_tet = models.CharField("Judul (Tetun)", max_length=80)
    judul_en = models.CharField("Judul (English)", max_length=80, blank=True)
    judul_pt = models.CharField("Judul (Português)", max_length=80, blank=True)
    judul_id = models.CharField("Judul (Indonesia)", max_length=80, blank=True)
    emoji = models.CharField(max_length=8, blank=True)
    aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ["level__nomor", "urutan"]
        verbose_name = "Materi"
        verbose_name_plural = "Materi"

    def __str__(self):
        return f"L{self.level.nomor}.{self.urutan} {self.judul_tet}"

    def judul(self, bahasa=BAHASA_DEFAULT):
        return teks_bahasa(self, "judul", bahasa)


class Kalimat(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draf (belum dicek penutur asli)"
        TERVERIFIKASI = "terverifikasi", "Terverifikasi penutur asli"

    materi = models.ForeignKey(Materi, on_delete=models.CASCADE, related_name="kalimat")
    urutan = models.PositiveSmallIntegerField(default=1)
    teks_tet = models.CharField("Tetun", max_length=300)
    teks_en = models.CharField("English", max_length=300, blank=True)
    teks_pt = models.CharField("Português", max_length=300, blank=True)
    teks_id = models.CharField("Indonesia", max_length=300, blank=True)
    emoji = models.CharField("Gambar (emoji)", max_length=8, blank=True, help_text="Gambar bantu untuk yang belum lancar membaca")
    # Suara contoh. Kosong = tombol 'Dengar' memakai suara bawaan HP bila ada (Tetun biasanya TIDAK ada -> rekam penutur asli!)
    audio_tet = models.FileField(upload_to="audio/kalimat/", blank=True)
    audio_en = models.FileField(upload_to="audio/kalimat/", blank=True)
    audio_pt = models.FileField(upload_to="audio/kalimat/", blank=True)
    audio_id = models.FileField(upload_to="audio/kalimat/", blank=True)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.DRAFT)
    untuk_crowdsource = models.BooleanField(
        "Tampil di halaman 'Bantu AI'", default=True,
        help_text="Kalimat ini boleh diminta direkam dalam bahasa daerah.")
    aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ["materi__level__nomor", "materi__urutan", "urutan"]
        verbose_name = "Kalimat"
        verbose_name_plural = "Kalimat"

    def __str__(self):
        return self.teks_tet[:50]

    def teks(self, bahasa=BAHASA_DEFAULT):
        return teks_bahasa(self, "teks", bahasa)

    @property
    def level(self):
        return self.materi.level


# ==================================================================== KARAKTER AI
class KarakterAI(models.Model):
    class Kode(models.TextChoices):
        PREMAN = "preman", "AI Preman"
        SOPAN = "sopan", "AI Sopan"
        PROFESIONAL = "profesional", "AI Profesional"

    kode = models.CharField(max_length=12, choices=Kode.choices, unique=True)
    nama_tet = models.CharField(max_length=60)
    nama_en = models.CharField(max_length=60, blank=True)
    nama_pt = models.CharField(max_length=60, blank=True)
    nama_id = models.CharField(max_length=60, blank=True)
    deskripsi_tet = models.CharField(max_length=200, blank=True)
    deskripsi_en = models.CharField(max_length=200, blank=True)
    deskripsi_pt = models.CharField(max_length=200, blank=True)
    deskripsi_id = models.CharField(max_length=200, blank=True)
    contoh_tet = models.CharField("Contoh ucapan (Tetun)", max_length=200, blank=True)
    contoh_en = models.CharField("Contoh ucapan (English)", max_length=200, blank=True)
    prompt_sistem = models.TextField(
        "Instruksi untuk AI (prompt)",
        help_text="Aturan gaya bicara yang dikirim ke model AI. Admin boleh mengubahnya kapan saja.")
    emoji = models.CharField(max_length=8, blank=True)
    warna = models.CharField(max_length=6, choices=Warna.choices, default=Warna.MERAH)
    aktif = models.BooleanField(default=True)
    diubah_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Karakter AI"
        verbose_name_plural = "Karakter AI"

    def __str__(self):
        return self.get_kode_display()

    def nama(self, bahasa=BAHASA_DEFAULT):
        return teks_bahasa(self, "nama", bahasa)

    def deskripsi(self, bahasa=BAHASA_DEFAULT):
        return teks_bahasa(self, "deskripsi", bahasa)


# ================================================================= REKAMAN SUARA
def validasi_ukuran_suara(berkas):
    if berkas.size > settings.SUARA_MAKS_BYTE:
        raise ValidationError(f"Berkas suara terlalu besar (maks {settings.SUARA_MAKS_BYTE // 1024 // 1024} MB).")


class RekamanSuara(models.Model):
    """
    Suara dari halaman 'Bantu AI Belajar Bahasa Kamu'.
    PRIVASI: yang disimpan HANYA bahasa, kalimat, file suara, dan gaya bicara. Tidak ada nama, HP, alamat.
    `pengirim_kode` hanya kode acak samaran (bukan relasi ke akun) supaya Admin bisa memblokir pengirim
    yang nakal. Peringatan jujur: karena kode itu juga ada di tabel Pengguna, orang yang memegang seluruh
    database dapat menghubungkannya. Karena itu akses database harus dibatasi, dan kode ini tidak ikut
    diekspor untuk pelatihan model.
    """

    class Status(models.TextChoices):
        MENUNGGU = "menunggu", "Menunggu"
        DISETUJUI = "disetujui", "Disetujui"
        DITOLAK = "ditolak", "Ditolak"

    kalimat = models.ForeignKey(Kalimat, on_delete=models.CASCADE, related_name="rekaman")
    bahasa = models.ForeignKey(Bahasa, on_delete=models.PROTECT, related_name="rekaman",
                               help_text="Bahasa yang diucapkan di rekaman")
    gaya = models.ForeignKey(KarakterAI, on_delete=models.PROTECT, related_name="rekaman", help_text="Gaya bicara")
    audio = models.FileField(upload_to="suara/%Y/%m/", validators=[validasi_ukuran_suara])
    mime_type = models.CharField(max_length=40, blank=True)
    durasi_detik = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.MENUNGGU, db_index=True)
    alasan_tolak = models.CharField(max_length=200, blank=True)
    transkripsi = models.TextField(
        "Transkripsi (teks dari suara)", blank=True,
        help_text="Diisi Admin/penutur asli: tulisan dari apa yang diucapkan. Pasangan suara+teks inilah yang berguna untuk melatih AI.")
    pengirim_kode = models.CharField(max_length=12, blank=True, db_index=True)
    ditinjau_oleh = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    ditinjau_pada = models.DateTimeField(null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dibuat_pada"]
        indexes = [models.Index(fields=["bahasa", "status"])]
        verbose_name = "Rekaman suara"
        verbose_name_plural = "Rekaman suara"

    def __str__(self):
        return f"{self.bahasa} / {self.kalimat} ({self.get_status_display()})"

    def tinjau(self, status, oleh, alasan=""):
        """Setujui / tolak oleh Admin."""
        self.status, self.ditinjau_oleh, self.ditinjau_pada = status, oleh, timezone.now()
        self.alasan_tolak = alasan if status == self.Status.DITOLAK else ""
        self.save(update_fields=["status", "ditinjau_oleh", "ditinjau_pada", "alasan_tolak"])


# ================================================================ PROGRES BELAJAR
class ProgresBelajar(models.Model):
    pengguna = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progres")
    kalimat = models.ForeignKey(Kalimat, on_delete=models.CASCADE, related_name="+")
    selesai_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["pengguna", "kalimat"], name="satu_progres_per_kalimat")]
        verbose_name = "Progres belajar"
        verbose_name_plural = "Progres belajar"

    def __str__(self):
        return f"{self.pengguna} - {self.kalimat}"
