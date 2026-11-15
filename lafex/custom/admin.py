from django.contrib import admin

from belajar.models import Kalimat
from .models import Bahasa, KarakterAI, Level, Materi


@admin.register(Bahasa)
class BahasaAdmin(admin.ModelAdmin):
	list_display = ('nama', 'kode', 'jenis', 'untuk_crowdsource', 'perlu_verifikasi', 'aktif', 'urutan')
	list_filter = ('jenis', 'untuk_crowdsource', 'perlu_verifikasi', 'aktif')
	list_editable = ('aktif', 'urutan')
	search_fields = ('nama', 'kode')


class MateriInline(admin.TabularInline):
	model = Materi
	extra = 0
	fields = ('urutan', 'judul_tet', 'judul_en', 'judul_pt', 'judul_id', 'emoji', 'aktif')


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
	list_display = ('nomor', 'emoji', 'judul_tet', 'judul_en', 'warna', 'aktif')
	inlines = [MateriInline]


class KalimatInline(admin.StackedInline):
	model = Kalimat
	extra = 0
	fields = (('urutan', 'emoji', 'status', 'aktif'), 'teks_tet', 'teks_en', 'teks_pt', 'teks_id',
			  ('audio_tet', 'audio_en'), ('audio_pt', 'audio_id'))


@admin.register(Materi)
class MateriAdmin(admin.ModelAdmin):
	list_display = ('__str__', 'level', 'urutan', 'aktif')
	list_filter = ('level',)
	inlines = [KalimatInline]


@admin.register(KarakterAI)
class KarakterAIAdmin(admin.ModelAdmin):
	list_display = ('kode', 'nama_tet', 'aktif', 'diubah_pada')
	fieldsets = (
		(None, {'fields': ('kode', 'emoji', 'warna', 'aktif')}),
		('Nama & deskripsi (ditampilkan ke user)', {'fields': (
			('nama_tet', 'nama_en', 'nama_pt', 'nama_id'),
			('deskripsi_tet', 'deskripsi_en'), ('deskripsi_pt', 'deskripsi_id'),
			('contoh_tet', 'contoh_en'))}),
		('Gaya bicara AI', {'fields': ('prompt_sistem',)}),
	)
