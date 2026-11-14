"""Admin dasar. Dashboard Admin khusus (grafik, dengar-setujui suara) menyusul di tahap berikutnya."""
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .models import Bahasa, KarakterAI, Level, Materi, Pengguna, ProgresBelajar, Kalimat, RekamanSuara


@admin.register(Pengguna)
class PenggunaAdmin(UserAdmin):
    list_display = ("username", "email", "telepon", "peran", "is_tamu", "is_active", "date_joined")
    list_filter = ("peran", "is_tamu", "is_active")
    search_fields = ("username", "email", "telepon", "kode_anonim")
    fieldsets = UserAdmin.fieldsets + (("Lian Timor", {"fields": ("peran", "bahasa_ui", "telepon", "is_tamu")}),)
    readonly_fields = ("kode_anonim",)
    actions = ["nonaktifkan", "aktifkan"]

    @admin.action(description="Matikan pengguna terpilih (tidak bisa masuk)")
    def nonaktifkan(self, request, queryset):
        n = queryset.exclude(is_superuser=True).update(is_active=False)
        self.message_user(request, f"{n} pengguna dimatikan.", messages.SUCCESS)

    @admin.action(description="Aktifkan lagi pengguna terpilih")
    def aktifkan(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_active=True)} pengguna diaktifkan.", messages.SUCCESS)


@admin.register(Bahasa)
class BahasaAdmin(admin.ModelAdmin):
    list_display = ("nama", "kode", "jenis", "untuk_crowdsource", "perlu_verifikasi", "aktif", "urutan")
    list_filter = ("jenis", "untuk_crowdsource", "perlu_verifikasi", "aktif")
    list_editable = ("aktif", "urutan")
    search_fields = ("nama", "kode")


class MateriInline(admin.TabularInline):
    model = Materi
    extra = 0
    fields = ("urutan", "judul_tet", "judul_en", "judul_pt", "judul_id", "emoji", "aktif")


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("nomor", "emoji", "judul_tet", "judul_en", "warna", "aktif")
    inlines = [MateriInline]


class KalimatInline(admin.StackedInline):
    model = Kalimat
    extra = 0
    fields = (("urutan", "emoji", "status", "aktif"), "teks_tet", "teks_en", "teks_pt", "teks_id",
              ("audio_tet", "audio_en"), ("audio_pt", "audio_id"))


@admin.register(Materi)
class MateriAdmin(admin.ModelAdmin):
    list_display = ("__str__", "level", "urutan", "aktif")
    list_filter = ("level",)
    inlines = [KalimatInline]


@admin.register(Kalimat)
class KalimatAdmin(admin.ModelAdmin):
    list_display = ("teks_tet", "teks_en", "materi", "status", "untuk_crowdsource", "aktif")
    list_filter = ("materi__level", "status", "untuk_crowdsource", "aktif")
    search_fields = ("teks_tet", "teks_en", "teks_pt", "teks_id")


@admin.register(KarakterAI)
class KarakterAIAdmin(admin.ModelAdmin):
    list_display = ("kode", "nama_tet", "aktif", "diubah_pada")
    fieldsets = (
        (None, {"fields": ("kode", "emoji", "warna", "aktif")}),
        ("Nama & deskripsi (ditampilkan ke user)", {"fields": (
            ("nama_tet", "nama_en", "nama_pt", "nama_id"),
            ("deskripsi_tet", "deskripsi_en"), ("deskripsi_pt", "deskripsi_id"),
            ("contoh_tet", "contoh_en"))}),
        ("Gaya bicara AI", {"fields": ("prompt_sistem",)}),
    )


@admin.action(description="Setujui rekaman terpilih")
def setujui(modeladmin, request, queryset):
    for r in queryset:
        r.tinjau(RekamanSuara.Status.DISETUJUI, request.user)


@admin.action(description="Tolak rekaman terpilih")
def tolak(modeladmin, request, queryset):
    for r in queryset:
        r.tinjau(RekamanSuara.Status.DITOLAK, request.user, "Ditolak admin")


@admin.action(description="Matikan pengirim rekaman terpilih (pengguna nakal)")
def matikan_pengirim(modeladmin, request, queryset):
    kode = set(queryset.exclude(pengirim_kode="").values_list("pengirim_kode", flat=True))
    n = Pengguna.objects.filter(kode_anonim__in=kode).exclude(is_superuser=True).update(is_active=False)
    queryset.update(status=RekamanSuara.Status.DITOLAK, alasan_tolak="Pengirim dimatikan")
    modeladmin.message_user(request, f"{n} pengguna dimatikan.", messages.WARNING)


@admin.register(RekamanSuara)
class RekamanSuaraAdmin(admin.ModelAdmin):
    list_display = ("dengar", "bahasa", "kalimat", "gaya", "status", "dibuat_pada", "pengirim_kode")
    list_filter = ("status", "bahasa", "gaya")
    search_fields = ("kalimat__teks_tet", "transkripsi", "pengirim_kode")
    readonly_fields = ("dengar", "pengirim_kode", "ditinjau_oleh", "ditinjau_pada", "dibuat_pada", "mime_type", "durasi_detik")
    actions = [setujui, tolak, matikan_pengirim]

    @admin.display(description="Dengar")
    def dengar(self, obj):
        if not obj.audio:
            return "-"
        return format_html('<audio controls preload="none" src="{}" style="height:32px"></audio>', obj.audio.url)

    def has_add_permission(self, request):
        return False   # suara hanya masuk lewat halaman crowdsource


@admin.register(ProgresBelajar)
class ProgresBelajarAdmin(admin.ModelAdmin):
    """Hanya untuk dilihat (laporan); progres dibuat otomatis saat user belajar."""
    list_display = ("pengguna", "kalimat", "selesai_pada")
    list_filter = ("kalimat__materi__level",)
    readonly_fields = ("pengguna", "kalimat", "selesai_pada")

    def has_add_permission(self, request):
        return False
