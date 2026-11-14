from django.contrib.auth.models import User
from django.db import models

from custom.models import KarakterAI


class Giliran(models.Model):
	"""
	Satu giliran bicara: ucapan user + jawaban AI. Dipakai untuk (1) konteks percakapan, (2) batas pemakaian harian
	supaya biaya token terkendali, (3) riwayat yang bisa dihapus user. Yang disimpan TEKS saja; suara user tidak disimpan.
	"""
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='giliran_ai')
	karakter = models.ForeignKey(KarakterAI, on_delete=models.PROTECT, related_name='giliran', verbose_name="Karakter AI")
	bahasa_ucap = models.CharField(max_length=3, default='tet', verbose_name="Lian ne'ebé user ko'alia")
	ucapan = models.TextField(verbose_name="Ucapan user")
	jawab_tet = models.TextField(verbose_name="Jawaban (Tetun)")
	jawab_en = models.TextField(blank=True, verbose_name="Jawaban (English)")
	koreksi = models.TextField(blank=True, verbose_name="Koresaun")
	demo = models.BooleanField(default=False, help_text="Jawaban contoh dari mode demo (bukan dari model AI)")
	model = models.CharField(max_length=60, blank=True)
	token_masuk = models.PositiveIntegerField(default=0)
	token_keluar = models.PositiveIntegerField(default=0)
	datetime = models.DateTimeField(auto_now_add=True, db_index=True)

	class Meta:
		ordering = ['datetime', 'id']
		verbose_name = "Giliran AI"
		verbose_name_plural = "Giliran AI"

	def __str__(self):
		template = '{0.user} - {0.ucapan}'
		return template.format(self)[:60]
