import secrets

from django.contrib.auth.models import User
from django.db import models


def kode_acak():
	"""Kode samaran 12 karakter untuk pengirim suara (bukan nama/HP/email)."""
	return secrets.token_hex(6)


class Perfil(models.Model):
	"""
	Data tambahan untuk User bawaan Django (pola sama dengan FunsionarioUser di SJDF).
	Group (admin / kontributor / pelajar) memakai Group bawaan Django, dibatasi dengan @allowed_users.
	Nomor HP TIDAK diverifikasi lewat SMS (butuh layanan berbayar); hanya pengenal login bersama password.
	"""
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
	peran = models.CharField(choices=[('anak', 'Labarik eskola'), ('dewasa', 'Ema boot'),
									  ('guru', 'Profesór'), ('ibu_pasar', 'Inan iha merkadu')],
							 max_length=12, blank=True, verbose_name="Ha'u mak",
							 help_text="Dijawab user: 'Kamu siapa?'. Dipakai untuk menyesuaikan materi.")
	bahasa_ui = models.CharField(choices=[('tet', 'Tetun'), ('en', 'English'), ('pt', 'Português'), ('id', 'Bahasa Indonesia')],
								 max_length=3, default='tet', verbose_name="Lian aplikasaun")
	telepon = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="Nu. Telefone",
							   help_text="Format +670xxxxxxxx. Kosong jika daftar dengan email.")
	is_tamu = models.BooleanField(default=False, verbose_name="Konvidadu (la regista)",
								  help_text="Dibuat otomatis oleh tombol 'Lanjut tanpa daftar'.")
	kode_anonim = models.CharField(max_length=12, unique=True, default=kode_acak, editable=False,
								   help_text="Kode samaran. Dipakai di RekamanSuara agar Admin bisa memblokir pengirim nakal tanpa melihat identitasnya.")
	datetime = models.DateTimeField(auto_now_add=True, null=True)

	class Meta:
		verbose_name = "Perfil"
		verbose_name_plural = "Perfil"

	def __str__(self):
		template = '{0.user.username}'
		return template.format(self)


class PengajuanKontributor(models.Model):
	"""
	Pelajar (bukan tamu) mengajukan diri menjadi kontributor suara. Admin menyetujui/menolak di halaman Pengajuan.
	Disetujui -> group user dipindah dari pelajar ke kontributor (satu group per user, seperti SJDF).
	"""
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pengajuan')
	bahasa = models.ForeignKey('custom.Bahasa', on_delete=models.PROTECT, related_name='+', verbose_name="Lian ne'ebé ha'u koalia")
	alasan = models.CharField(max_length=300, verbose_name="Razaun / esperiénsia")
	status = models.CharField(choices=[('menunggu', 'Hein'), ('disetujui', 'Aprova'), ('ditolak', 'Rejeita')],
							  max_length=10, default='menunggu', db_index=True)
	catatan = models.CharField(max_length=200, blank=True, verbose_name="Razaun rejeita")
	ditinjau_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
	ditinjau_pada = models.DateTimeField(null=True, blank=True)
	datetime = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-datetime']
		verbose_name = "Pengajuan kontributor"
		verbose_name_plural = "Pengajuan kontributor"

	def __str__(self):
		template = '{0.user.username} / {0.bahasa} ({0.status})'
		return template.format(self)
