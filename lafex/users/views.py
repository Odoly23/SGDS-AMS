from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.decorators import allowed_users, unauthenticated_user
from config.user_utils import GRUP_ADMIN, GRUP_KONTRIBUTOR, GRUP_PELAJAR, SEMUA_GRUP, buat_user, nama_grup, pastikan_grup
from users.forms import DaftarForm
from custom.models import Bahasa
from django.http import Http404
from django.utils import timezone
from users.models import Perfil, PengajuanKontributor

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


# ---------------------------------------------------------------- Ajukan jadi kontributor
MAKS_PENGAJUAN = 3        # per akun, supaya admin tidak dibanjiri


@login_required
@allowed_users(allowed_roles=[GRUP_PELAJAR])
def Ajukan(request):
	"""Pelajar (bukan tamu) mengajukan diri menjadi kontributor. Satu pengajuan menunggu pada satu waktu."""
	perfil, _ = Perfil.objects.get_or_create(user=request.user)
	riwayat = list(request.user.pengajuan.select_related('bahasa'))
	menunggu = next((x for x in riwayat if x.status == 'menunggu'), None)
	bahasa_list = Bahasa.objects.filter(aktif=True, untuk_crowdsource=True)
	galat = ''
	if request.method == 'POST':
		bahasa = bahasa_list.filter(kode=request.POST.get('bahasa', '')).first()
		alasan = request.POST.get('alasan', '').strip()
		if perfil.is_tamu or menunggu or len(riwayat) >= MAKS_PENGAJUAN:
			galat = 'err_apply_blocked'
		elif not bahasa or len(alasan) < 5:
			galat = 'err_apply_invalid'
		else:
			PengajuanKontributor.objects.create(user=request.user, bahasa=bahasa, alasan=alasan[:300])
			messages.success(request, 'msg_apply_sent')
			return redirect('user-ajukan')
	context = {'group': nama_grup(request.user), 'page': 'account', 'title': 'Aplika kontributór', 'perfil': perfil,
	           'riwayat': riwayat, 'menunggu': menunggu, 'bahasa_list': bahasa_list, 'galat': galat,
	           'boleh': not (perfil.is_tamu or menunggu or len(riwayat) >= MAKS_PENGAJUAN)}
	return render(request, 'users/ajukan.html', context)


@login_required
@allowed_users(allowed_roles=[GRUP_ADMIN])
def Pengajuan(request):
	status = request.GET.get('status', 'menunggu')
	if status not in ('menunggu', 'disetujui', 'ditolak', 'semua'):
		status = 'menunggu'
	qs = PengajuanKontributor.objects.select_related('user', 'bahasa')
	if status != 'semua':
		qs = qs.filter(status=status)
	hal = Paginator(qs.order_by('datetime'), 15).get_page(request.GET.get('hal'))
	context = {'group': nama_grup(request.user), 'page': 'users', 'title': 'Pengajuan kontributor', 'status': status, 'halaman': hal,
	           'jumlah': {s: PengajuanKontributor.objects.filter(status=s).count() for s in ('menunggu', 'disetujui', 'ditolak')}}
	return render(request, 'users/pengajuan.html', context)


@login_required
@allowed_users(allowed_roles=[GRUP_ADMIN])
@require_POST
def PengajuanAksi(request, pk):
	p = get_object_or_404(PengajuanKontributor, pk=pk)
	aksi = request.POST.get('aksi', '')
	if aksi not in ('setujui', 'tolak'):
		raise Http404
	if p.status != 'menunggu':
		return redirect('u-pengajuan')
	if aksi == 'setujui':
		if p.user.groups.filter(name=GRUP_ADMIN).exists() or p.user.is_superuser:
			messages.error(request, 'err_admin_protect')
			return redirect('u-pengajuan')
		grup = pastikan_grup()
		p.user.groups.set([grup[GRUP_KONTRIBUTOR]])                # satu group per user
		p.status, p.catatan = 'disetujui', ''
	else:
		p.status, p.catatan = 'ditolak', request.POST.get('catatan', '').strip()[:200]
	p.ditinjau_oleh, p.ditinjau_pada = request.user, timezone.now()
	p.save()
	messages.success(request, 'msg_saved')
	return redirect('u-pengajuan')
