from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.decorators import allowed_users, unauthenticated_user
from config.user_utils import GRUP_ADMIN, SEMUA_GRUP, buat_user, nama_grup
from users.forms import DaftarForm
from users.models import Perfil

PERAN = [('anak', 'role_anak', 'fa-graduation-cap'), ('dewasa', 'role_dewasa', 'fa-user'),
		 ('guru', 'role_guru', 'fa-pencil'), ('ibu_pasar', 'role_ibu_pasar', 'fa-shopping-basket')]


@unauthenticated_user
def Register(request):
	if request.method == 'POST':
		form = DaftarForm(request.POST)
		if form.is_valid():
			user = buat_user(form.kontak_normal, form.cleaned_data['password1'])
			auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
			messages.success(request, 'msg_account_created')
			return redirect('home')
	else:
		form = DaftarForm()
	return render(request, 'auth/register.html', {'form': form, 'title': 'Regista'})


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
def Peran(request):
	"""'Kamu siapa?': Anak Sekolah / Dewasa / Guru / Ibu di Pasar. Dipakai untuk menyesuaikan materi."""
	perfil, _ = Perfil.objects.get_or_create(user=request.user)
	if request.method == 'POST':
		pilihan = request.POST.get('peran')
		if pilihan in dict((k, v) for k, v, _ in PERAN):
			perfil.peran = pilihan
			perfil.save(update_fields=['peran'])
			return redirect('home')
		messages.error(request, 'err_choose_one')
	context = {'group': nama_grup(request.user), 'peran_list': PERAN, 'peran_sekarang': perfil.peran, 'title': 'Ita nain sé?'}
	return render(request, 'auth/peran.html', context)


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
def Account(request):
	perfil, _ = Perfil.objects.get_or_create(user=request.user)
	context = {'group': nama_grup(request.user), 'page': 'account', 'perfil': perfil, 'title': "Ha'u nia konta"}
	return render(request, 'auth/account.html', context)


@login_required
@allowed_users(allowed_roles=[GRUP_ADMIN])
def UserList(request):
	objects = User.objects.select_related('perfil').prefetch_related('groups').order_by('-date_joined')[:300]
	context = {'group': nama_grup(request.user), 'page': 'users', 'objects': objects, 'title': 'Lista utilizadór'}
	return render(request, 'users/list.html', context)


@login_required
@allowed_users(allowed_roles=[GRUP_ADMIN])
@require_POST
def UserToggle(request, pk):
	"""Admin mematikan / mengaktifkan lagi pengguna (mis. yang nakal). Admin lain tidak bisa dimatikan lewat sini."""
	obj = get_object_or_404(User, id=pk)
	if obj.is_superuser or obj.pk == request.user.pk or obj.groups.filter(name=GRUP_ADMIN).exists():
		messages.error(request, 'err_admin_protect')
	else:
		obj.is_active = not obj.is_active
		obj.save(update_fields=['is_active'])
		messages.success(request, 'msg_user_unblocked' if obj.is_active else 'msg_user_blocked')
	return redirect('u-list')
