from django.db import models

# Data master (pilihan/lookup) Lian Timor. Mirip app `custom` di SJDF.
# Teks yang tampil ke user disimpan 4 kolom (_tet, _en, _pt, _id); bahasa daerah TIDAK jadi kolom,
# melainkan lewat crowdsource.RekamanSuara.


def teks_bahasa(obj, awalan, bahasa):
	"""Ambil obj.<awalan>_<bahasa>; kalau kosong jatuh ke Tetun, lalu bahasa lain yang terisi."""
	for kode in (bahasa, 'tet', 'en', 'pt', 'id'):
		nilai = getattr(obj, f'{awalan}_{kode}', '')
		if nilai:
			return nilai
	return ''


class Warna(models.TextChoices):
	"""Warna kartu (bendera & tais), dipetakan ke kelas CSS .kartu-merah dst. di main.css"""
	MERAH = 'merah', 'Merah'
	KUNING = 'kuning', 'Kuning'
	HITAM = 'hitam', 'Hitam'
	PUTIH = 'putih', 'Putih'


class Bahasa(models.Model):
	kode = models.SlugField(max_length=30, unique=True, verbose_name="Kódigu", help_text="Contoh: tet, en, mambae")
	nama = models.CharField(max_length=80, verbose_name="Naran Lian")
	nama_asli = models.CharField(max_length=80, blank=True, verbose_name="Naran iha lian rasik")
	jenis = models.CharField(choices=[('ui', 'Lian aplikasaun'), ('lokal', 'Lian rejionál')], max_length=6,
							 default='lokal', verbose_name="Tipu")
	iso_639_3 = models.CharField(max_length=3, blank=True, verbose_name="Kódigu ISO 639-3")
	untuk_crowdsource = models.BooleanField(default=True, verbose_name="Hatudu iha 'Ajuda AI'")
	perlu_verifikasi = models.BooleanField(default=False, verbose_name="Naran presiza verifika",
										   help_text="Centang jika belum pasti ini bahasa tersendiri (bukan dialek/nama desa). Cek ke INL-UNTL.")
	catatan = models.TextField(blank=True, verbose_name="Nota linguístika")
	aktif = models.BooleanField(default=True, verbose_name="Ativu")
	urutan = models.PositiveIntegerField(default=100, verbose_name="Orden")

	class Meta:
		ordering = ['urutan', 'nama']
		verbose_name = "Lian"
		verbose_name_plural = "Lian"

	def __str__(self):
		template = '{0.nama}'
		return template.format(self)


class Level(models.Model):
	TARGET_KALIMAT = 20   # setiap Level sebaiknya berisi 20 kalimat

	nomor = models.PositiveSmallIntegerField(unique=True, verbose_name="Nu. Nivel", help_text="1 sampai 5")
	judul_tet = models.CharField(max_length=80, verbose_name="Títulu (Tetun)")
	judul_en = models.CharField(max_length=80, blank=True, verbose_name="Títulu (English)")
	judul_pt = models.CharField(max_length=80, blank=True, verbose_name="Títulu (Português)")
	judul_id = models.CharField(max_length=80, blank=True, verbose_name="Títulu (Indonesia)")
	emoji = models.CharField(max_length=8, blank=True, verbose_name="Imajen (emoji)", help_text="Gambar besar di kartu, mis. 🥬")
	warna = models.CharField(max_length=6, choices=Warna.choices, default=Warna.MERAH, verbose_name="Kór")
	aktif = models.BooleanField(default=True, verbose_name="Ativu")

	class Meta:
		ordering = ['nomor']
		verbose_name = "Nivel"
		verbose_name_plural = "Nivel"

	def __str__(self):
		template = 'Nivel {0.nomor}: {0.judul_tet}'
		return template.format(self)

	def judul(self, bahasa='tet'):
		return teks_bahasa(self, 'judul', bahasa)

	@property
	def total_kalimat(self):
		from belajar.models import Kalimat
		return Kalimat.objects.filter(materi__level=self, materi__aktif=True, aktif=True).count()


class Materi(models.Model):
	"""Kelompok kecil kalimat di dalam satu Level (mis. 'Menawar harga'). Opsional, memudahkan Admin."""
	level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='materi', verbose_name="Nivel")
	urutan = models.PositiveSmallIntegerField(default=1, verbose_name="Orden")
	judul_tet = models.CharField(max_length=80, verbose_name="Títulu (Tetun)")
	judul_en = models.CharField(max_length=80, blank=True, verbose_name="Títulu (English)")
	judul_pt = models.CharField(max_length=80, blank=True, verbose_name="Títulu (Português)")
	judul_id = models.CharField(max_length=80, blank=True, verbose_name="Títulu (Indonesia)")
	emoji = models.CharField(max_length=8, blank=True, verbose_name="Imajen (emoji)")
	aktif = models.BooleanField(default=True, verbose_name="Ativu")

	class Meta:
		ordering = ['level__nomor', 'urutan']
		verbose_name = "Matéria"
		verbose_name_plural = "Matéria"

	def __str__(self):
		template = 'N{0.level.nomor}.{0.urutan} {0.judul_tet}'
		return template.format(self)

	def judul(self, bahasa='tet'):
		return teks_bahasa(self, 'judul', bahasa)


class KarakterAI(models.Model):
	"""3 karakter AI. Admin boleh mengubah teks & instruksinya kapan saja."""
	kode = models.CharField(choices=[('preman', 'AI Preman'), ('sopan', 'AI Sopan'), ('profesional', 'AI Profesional')],
							max_length=12, unique=True, verbose_name="Kódigu")
	nama_tet = models.CharField(max_length=60, verbose_name="Naran (Tetun)")
	nama_en = models.CharField(max_length=60, blank=True, verbose_name="Naran (English)")
	nama_pt = models.CharField(max_length=60, blank=True, verbose_name="Naran (Português)")
	nama_id = models.CharField(max_length=60, blank=True, verbose_name="Naran (Indonesia)")
	deskripsi_tet = models.CharField(max_length=200, blank=True, verbose_name="Deskrisaun (Tetun)")
	deskripsi_en = models.CharField(max_length=200, blank=True, verbose_name="Deskrisaun (English)")
	deskripsi_pt = models.CharField(max_length=200, blank=True, verbose_name="Deskrisaun (Português)")
	deskripsi_id = models.CharField(max_length=200, blank=True, verbose_name="Deskrisaun (Indonesia)")
	contoh_tet = models.CharField(max_length=200, blank=True, verbose_name="Ezemplu fraze (Tetun)")
	contoh_en = models.CharField(max_length=200, blank=True, verbose_name="Ezemplu fraze (English)")
	prompt_sistem = models.TextField(verbose_name="Instrusaun ba AI (prompt)",
									 help_text="Aturan gaya bicara yang dikirim ke model AI. Admin boleh mengubahnya kapan saja.")
	emoji = models.CharField(max_length=8, blank=True, verbose_name="Imajen (emoji)")
	warna = models.CharField(max_length=6, choices=Warna.choices, default=Warna.MERAH, verbose_name="Kór")
	aktif = models.BooleanField(default=True, verbose_name="Ativu")
	diubah_pada = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Karakter AI"
		verbose_name_plural = "Karakter AI"

	def __str__(self):
		template = '{0.nama_tet}'
		return template.format(self)

	def nama(self, bahasa='tet'):
		return teks_bahasa(self, 'nama', bahasa)

	def deskripsi(self, bahasa='tet'):
		return teks_bahasa(self, 'deskripsi', bahasa)
