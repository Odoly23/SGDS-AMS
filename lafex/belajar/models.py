from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models

from custom.models import Materi, teks_bahasa
from config.utils import kalimat_audio

AUDIO_OK = FileExtensionValidator(allowed_extensions=['mp3', 'ogg', 'wav', 'webm', 'm4a'])


class Kalimat(models.Model):
	materi = models.ForeignKey(Materi, on_delete=models.CASCADE, related_name='kalimat', verbose_name="Matéria")
	urutan = models.PositiveSmallIntegerField(default=1, verbose_name="Orden")
	teks_tet = models.CharField(max_length=300, verbose_name="Tetun")
	teks_en = models.CharField(max_length=300, blank=True, verbose_name="English")
	teks_pt = models.CharField(max_length=300, blank=True, verbose_name="Português")
	teks_id = models.CharField(max_length=300, blank=True, verbose_name="Indonesia")
	emoji = models.CharField(max_length=8, blank=True, verbose_name="Imajen (emoji)", help_text="Gambar bantu untuk yang belum lancar membaca")
	# Suara contoh. Kosong = tombol 'Dengar' memakai suara bawaan HP bila ada (HP umumnya TIDAK punya suara Tetun -> rekam penutur asli)
	audio_tet = models.FileField(upload_to=kalimat_audio, blank=True, validators=[AUDIO_OK], verbose_name="Audio Tetun")
	audio_en = models.FileField(upload_to=kalimat_audio, blank=True, validators=[AUDIO_OK], verbose_name="Audio English")
	audio_pt = models.FileField(upload_to=kalimat_audio, blank=True, validators=[AUDIO_OK], verbose_name="Audio Português")
	audio_id = models.FileField(upload_to=kalimat_audio, blank=True, validators=[AUDIO_OK], verbose_name="Audio Indonesia")
	status = models.CharField(choices=[('draft', 'Draf (seidauk verifika)'), ('terverifikasi', 'Verifika ona husi ema nain')],
							  max_length=14, default='draft', verbose_name="Estadu")
	untuk_crowdsource = models.BooleanField(default=True, verbose_name="Hatudu iha 'Ajuda AI'",
											help_text="Kalimat ini boleh diminta direkam dalam bahasa daerah.")
	aktif = models.BooleanField(default=True, verbose_name="Ativu")

	class Meta:
		ordering = ['materi__level__nomor', 'materi__urutan', 'urutan']
		verbose_name = "Fraze"
		verbose_name_plural = "Fraze"

	def __str__(self):
		template = '{0.teks_tet}'
		return template.format(self)[:60]

	def teks(self, bahasa='tet'):
		return teks_bahasa(self, 'teks', bahasa)

	@property
	def level(self):
		return self.materi.level


class ProgresBelajar(models.Model):
	"""Kalimat yang sudah dipelajari user (untuk progress bar 'sudah belajar 5 dari 20')."""
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progres')
	kalimat = models.ForeignKey(Kalimat, on_delete=models.CASCADE, related_name='+')
	datetime = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=['user', 'kalimat'], name='satu_progres_per_kalimat')]
		verbose_name = "Progresu"
		verbose_name_plural = "Progresu"

	def __str__(self):
		template = '{0.user} - {0.kalimat}'
		return template.format(self)
