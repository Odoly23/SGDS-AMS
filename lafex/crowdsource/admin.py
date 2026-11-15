from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.utils.html import format_html

from users.models import Perfil
from .models import RekamanSuara


@admin.action(description="Setujui rekaman terpilih")
def setujui(modeladmin, request, queryset):
	for r in queryset:
		r.tinjau('disetujui', request.user)


@admin.action(description="Tolak rekaman terpilih")
def tolak(modeladmin, request, queryset):
	for r in queryset:
		r.tinjau('ditolak', request.user, 'Ditolak admin')


@admin.action(description="Matikan pengirim rekaman terpilih (pengguna nakal)")
def matikan_pengirim(modeladmin, request, queryset):
	kode = set(queryset.exclude(pengirim_kode='').values_list('pengirim_kode', flat=True))
	ids = Perfil.objects.filter(kode_anonim__in=kode).values_list('user_id', flat=True)
	n = User.objects.filter(id__in=ids, is_superuser=False).update(is_active=False)
	queryset.update(status='ditolak', alasan_tolak='Pengirim dimatikan')
	modeladmin.message_user(request, f'{n} pengguna dimatikan.', messages.WARNING)


@admin.register(RekamanSuara)
class RekamanSuaraAdmin(admin.ModelAdmin):
	list_display = ('dengar', 'bahasa', 'kalimat', 'gaya', 'status', 'datetime', 'pengirim_kode')
	list_filter = ('status', 'bahasa', 'gaya')
	search_fields = ('kalimat__teks_tet', 'transkripsi', 'pengirim_kode')
	readonly_fields = ('dengar', 'pengirim_kode', 'ditinjau_oleh', 'ditinjau_pada', 'datetime', 'mime_type', 'durasi_detik')
	actions = [setujui, tolak, matikan_pengirim]

	@admin.display(description="Dengar")
	def dengar(self, obj):
		if not obj.audio:
			return '-'
		return format_html('<audio controls preload="none" src="{}" style="height:32px"></audio>', obj.audio.url)

	def has_add_permission(self, request):
		return False   # suara hanya masuk lewat halaman crowdsource
