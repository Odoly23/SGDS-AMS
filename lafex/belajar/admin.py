from django.contrib import admin

from .models import Kalimat, ProgresBelajar


@admin.register(Kalimat)
class KalimatAdmin(admin.ModelAdmin):
	list_display = ('teks_tet', 'teks_en', 'materi', 'status', 'untuk_crowdsource', 'aktif')
	list_filter = ('materi__level', 'status', 'untuk_crowdsource', 'aktif')
	search_fields = ('teks_tet', 'teks_en', 'teks_pt', 'teks_id')


@admin.register(ProgresBelajar)
class ProgresBelajarAdmin(admin.ModelAdmin):
	"""Hanya untuk dilihat (laporan); progres dibuat otomatis saat user belajar."""
	list_display = ('user', 'kalimat', 'datetime')
	list_filter = ('kalimat__materi__level',)
	readonly_fields = ('user', 'kalimat', 'datetime')

	def has_add_permission(self, request):
		return False
