from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Perfil


class PerfilInline(admin.StackedInline):
	model = Perfil
	can_delete = False
	readonly_fields = ('kode_anonim',)


@admin.action(description="Matikan pengguna terpilih (tidak bisa masuk)")
def nonaktifkan(modeladmin, request, queryset):
	n = queryset.exclude(is_superuser=True).update(is_active=False)
	modeladmin.message_user(request, f'{n} pengguna dimatikan.', messages.SUCCESS)


@admin.action(description="Aktifkan lagi pengguna terpilih")
def aktifkan(modeladmin, request, queryset):
	modeladmin.message_user(request, f'{queryset.update(is_active=True)} pengguna diaktifkan.', messages.SUCCESS)


admin.site.unregister(User)


@admin.register(User)
class UserAdminLian(UserAdmin):
	inlines = [PerfilInline]
	list_display = ('username', 'email', 'is_active', 'date_joined')
	actions = [nonaktifkan, aktifkan]
