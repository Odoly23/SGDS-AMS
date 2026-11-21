import hashlib
import secrets

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.conf import settings

from config.decorators import allowed_users, unauthenticated_user
from config.user_utils import GRUP_PELAJAR, SEMUA_GRUP, nama_grup, normalisasi_kontak, pastikan_grup
from custom.models import Level

BATAS_GAGAL, JEDA_GAGAL = 6, 15 * 60     # 6 salah ketik per 15 menit -> sementara terkunci


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
def Home(request):
	perfil = getattr(request.user, 'perfil', None)
	if perfil and not perfil.peran:                  # setelah login: tanya "Kamu siapa?" (sekali)
		return redirect('user-peran')
	if settings.HOME_LANGSUNG_BICARA and nama_grup(request.user) == GRUP_PELAJAR:
		return redirect('video-call')                    # semua orang: langsung bicara, tanpa memilih menu
	context = {
		'group': nama_grup(request.user), 'page': 'home',
		'levels': Level.objects.filter(aktif=True), 'title': 'Varanda',
	}
	return render(request, 'home/home.html', context)


@unauthenticated_user
def Login(request):
	if request.method == 'POST':
		kunci = 'login-gagal:' + hashlib.sha1(f'{request.META.get("REMOTE_ADDR", "")}|{request.POST.get("kontak", "").strip().lower()}'.encode()).hexdigest()
		if cache.get(kunci, 0) >= BATAS_GAGAL:
			messages.error(request, 'err_login_locked')
		else:
			try:
				_, username = normalisasi_kontak(request.POST.get('kontak'))
			except ValueError as e:
				messages.error(request, 'err_contact_invalid')
			else:
				user = authenticate(request, username=username, password=request.POST.get('password', ''))
				if user is not None:
					cache.delete(kunci)
					auth_login(request, user)
					return redirect('home')
				cache.set(kunci, cache.get(kunci, 0) + 1, JEDA_GAGAL)
				messages.error(request, 'err_login_fail')   # pesan sama: tidak membocorkan akun mana yang ada
	return render(request, 'home/login.html', {'title': 'Tama', 'kontak': request.POST.get('kontak', '')})


@require_POST
def Logout(request):
	auth_logout(request)
	return render(request, 'home/logout.html', {'title': 'Sai'})


@unauthenticated_user
@require_POST
def Tamu(request):
	"""'Lanjut tanpa daftar': akun tamu sementara (group pelajar). Progres tersimpan di HP ini selama cookie ada."""
	# batas pembuatan akun tamu per alamat IP supaya tidak diisi bot
	kunci = f'tamu-baru:{request.META.get("REMOTE_ADDR", "")}'
	cache.add(kunci, 0, 60 * 60)
	if cache.incr(kunci) > 30:
		messages.error(request, 'err_guest_limit')
		return redirect('login')
	from users.models import Perfil
	user = User.objects.create_user(username=f'tamu-{secrets.token_hex(6)}')
	user.set_unusable_password()
	user.save()
	user.groups.add(pastikan_grup()[GRUP_PELAJAR])
	Perfil.objects.create(user=user, is_tamu=True)
	auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
	return redirect('home')


# ---------------------------------------------------------------- PWA
def Manifest(request):
	return HttpResponse(render_to_string('main/manifest.webmanifest'), content_type='application/manifest+json')


@never_cache
def ServiceWorker(request):
	"""Harus dilayani dari akar situs (/sw.js) agar cakupannya seluruh aplikasi."""
	resp = HttpResponse(render_to_string('main/sw.js', {'versi': settings.PWA_VERSI}), content_type='application/javascript')
	resp['Service-Worker-Allowed'] = '/'
	return resp


def Offline(request):
	return render(request, 'home/offline.html', {'title': 'Offline'})


# ------------------------------------------------------------ halaman galat
def error_403(request, exception=None):
	return render(request, 'home/403.html', status=403)


def error_404(request, exception=None):
	return render(request, 'home/404.html', status=404)


def error_500(request):
	return render(request, 'home/500.html', status=500)
