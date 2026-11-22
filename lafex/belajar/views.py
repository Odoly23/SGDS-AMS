from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from belajar.models import Kalimat, ProgresBelajar
from config.decorators import allowed_users
from config.user_utils import SEMUA_GRUP, nama_grup
from custom.models import Level, Materi

KALIMAT_AKTIF = dict(aktif=True, materi__aktif=True, materi__level__aktif=True)


def _hitung(user, level):
	"""(selesai, total) kalimat aktif milik satu level."""
	total = Kalimat.objects.filter(materi__level=level, **KALIMAT_AKTIF).count()
	selesai = ProgresBelajar.objects.filter(user=user, kalimat__materi__level=level, **{f'kalimat__{k}': v for k, v in KALIMAT_AKTIF.items()}).count()
	return selesai, total


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
def BelajarList(request):
	"""Pilih level: kartu besar bergambar + progress bar tiap level."""
	levels = list(Level.objects.filter(aktif=True))
	for l in levels:
		l.selesai, l.total = _hitung(request.user, l)
		l.persen = round(l.selesai * 100 / l.total) if l.total else 0
	context = {'group': nama_grup(request.user), 'page': 'belajar', 'levels': levels, 'title': 'Aprende'}
	return render(request, 'belajar/belajar.html', context)


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
def BelajarLevel(request, nomor):
	"""Isi satu level: kalimat dalam 4 bahasa + Dengar + Grava ha'u + 'Ha'u aprende ona'."""
	level = get_object_or_404(Level, nomor=nomor, aktif=True)
	materi_list = list(Materi.objects.filter(level=level, aktif=True).prefetch_related(
		Prefetch('kalimat', queryset=Kalimat.objects.filter(aktif=True), to_attr='kalimat_aktif')))
	sudah = set(ProgresBelajar.objects.filter(user=request.user, kalimat__materi__level=level).values_list('kalimat_id', flat=True))
	total = selesai = 0
	ada_draft = False
	for m in materi_list:
		for k in m.kalimat_aktif:
			k.sudah = k.id in sudah
			total += 1
			selesai += k.sudah
			ada_draft = ada_draft or k.status == 'draft'
	context = {
		'group': nama_grup(request.user), 'page': 'belajar', 'level': level, 'materi_list': [m for m in materi_list if m.kalimat_aktif],
		'total': total, 'selesai': selesai, 'persen': round(selesai * 100 / total) if total else 0, 'ada_draft': ada_draft,
		'title': f'Nivel {level.nomor}',
	}
	return render(request, 'belajar/level.html', context)


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
@require_POST
def ProgresSimpan(request, pk):
	"""Tandai kalimat 'sudah dipelajari' (atau batalkan dengan hapus=1). Mengembalikan hitungan terbaru untuk progress bar."""
	kalimat = get_object_or_404(Kalimat, id=pk, **KALIMAT_AKTIF)
	if request.POST.get('hapus') == '1':
		ProgresBelajar.objects.filter(user=request.user, kalimat=kalimat).delete()
	else:
		ProgresBelajar.objects.get_or_create(user=request.user, kalimat=kalimat)
	selesai, total = _hitung(request.user, kalimat.materi.level)
	return JsonResponse({'selesai': selesai, 'total': total, 'persen': round(selesai * 100 / total) if total else 0})
