from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from belajar.models import Kalimat
from custom.models import Bahasa, KarakterAI
from config.utils import rekaman_suara


def validasi_ukuran_suara(berkas):
	if berkas.size > settings.SUARA_MAKS_BYTE:
		raise ValidationError(f'Berkas suara terlalu besar (maks {settings.SUARA_MAKS_BYTE // 1024 // 1024} MB).')


class RekamanSuara(models.Model):
	"""
	Suara dari halaman 'Bantu AI Belajar Bahasa Kamu'.
	PRIVASI: yang disimpan HANYA bahasa, kalimat, file suara, dan gaya bicara. Tidak ada nama, HP, alamat.
	`pengirim_kode` hanya kode acak samaran (BUKAN relasi ke akun) supaya Admin bisa memblokir pengirim nakal.
	Peringatan jujur: kode yang sama juga ada di users.Perfil, jadi pemegang seluruh database tetap bisa
	menghubungkannya. Batasi akses database dan JANGAN ikutkan kolom ini saat mengekspor data untuk melatih AI.
	"""
	kalimat = models.ForeignKey(Kalimat, on_delete=models.CASCADE, related_name='rekaman', verbose_name="Fraze")
	bahasa = models.ForeignKey(Bahasa, on_delete=models.PROTECT, related_name='rekaman', verbose_name="Lian",
							   help_text="Bahasa yang diucapkan di rekaman")
	gaya = models.ForeignKey(KarakterAI, on_delete=models.PROTECT, related_name='rekaman', verbose_name="Estilu ko'alia")
	audio = models.FileField(upload_to=rekaman_suara, validators=[validasi_ukuran_suara,
							 FileExtensionValidator(allowed_extensions=['webm', 'ogg', 'mp3', 'm4a', 'wav'])], verbose_name="Audio")
	mime_type = models.CharField(max_length=40, blank=True)
	durasi_detik = models.FloatField(null=True, blank=True, verbose_name="Durasaun (segundu)")
	status = models.CharField(choices=[('menunggu', 'Hein'), ('disetujui', 'Aprova'), ('ditolak', 'Rejeita')],
							  max_length=10, default='menunggu', db_index=True, verbose_name="Estadu")
	alasan_tolak = models.CharField(max_length=200, blank=True, verbose_name="Razaun rejeita")
	transkripsi = models.TextField(blank=True, verbose_name="Transkrisaun (teks dari suara)",
								   help_text="Diisi Admin/penutur asli: tulisan dari apa yang diucapkan. Pasangan suara+teks inilah yang berguna untuk melatih AI.")
	sumber_transkripsi = models.CharField(choices=[('', '-'), ('kontributor', 'Kontributor'), ('otomatis', 'Whisper (draf)'), ('admin', 'Diperiksa admin')],
								  max_length=12, blank=True, default='', verbose_name="Sumber transkripsi",
								  help_text="'Whisper (draf)' BELUM boleh dipakai melatih model; harus diperiksa manusia dulu.")
	pengirim_kode = models.CharField(max_length=12, blank=True, db_index=True)
	ditinjau_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
	ditinjau_pada = models.DateTimeField(null=True, blank=True)
	datetime = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-datetime']
		indexes = [models.Index(fields=['bahasa', 'status'])]
		verbose_name = "Rekaman Lian"
		verbose_name_plural = "Rekaman Lian"

	def __str__(self):
		template = '{0.bahasa} / {0.kalimat} ({0.status})'
		return template.format(self)

	def tinjau(self, status, oleh, alasan=''):
		"""Setujui / tolak oleh Admin."""
		self.status, self.ditinjau_oleh, self.ditinjau_pada = status, oleh, timezone.now()
		self.alasan_tolak = alasan if status == 'ditolak' else ''
		self.save(update_fields=['status', 'ditinjau_oleh', 'ditinjau_pada', 'alasan_tolak'])
