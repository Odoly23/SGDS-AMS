import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from ai import llm
from ai.models import Giliran
from config.decorators import allowed_users
from config.user_utils import SEMUA_GRUP, nama_grup
from custom.models import KarakterAI
from users.models import Perfil

BAHASA_UCAP = ('tet', 'en', 'pt', 'id')


def _perfil(user):
	return Perfil.objects.get_or_create(user=user)[0]


def _batas(perfil):
	return settings.AI['BATAS_HARI_TAMU'] if perfil.is_tamu else settings.AI['BATAS_HARI']


def _terpakai_hari_ini(user):
	mulai = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
	return Giliran.objects.filter(user=user, datetime__gte=mulai).count()


def _baris(g):
	return {'ucapan': g.ucapan, 'tet': g.jawab_tet, 'en': g.jawab_en, 'koreksi': g.koreksi, 'gerak': g.gerak, 'demo': g.demo}


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
def AiChat(request):
	"""Pilih karakter AI lalu bicara langsung dengan lafaek."""
	perfil = _perfil(request.user)
	context = {
		'group': nama_grup(request.user), 'page': 'ai', 'title': "Ko'alia ho AI",
		'karakter_list': KarakterAI.objects.filter(aktif=True),
		'sisa': max(0, _batas(perfil) - _terpakai_hari_ini(request.user)),
		'demo': settings.AI['BACKEND'] == 'dummy',
		'maks_teks': settings.AI['MAKS_TEKS'],
	}
	return render(request, 'ai/ai_chat.html', context)


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
@require_POST
def Bicara(request):
	"""Satu giliran: terima teks ucapan -> jawaban AI (Tetun + Inggris + koreksi)."""
	def galat(kode, status, **ekstra):
		return JsonResponse({'ok': False, 'kode': kode, **ekstra}, status=status)

	try:
		d = json.loads(request.body or b'{}')
	except ValueError:
		return galat('tidak_valid', 400)
	ucapan = str(d.get('teks', '')).strip()
	bahasa = d.get('bahasa') if d.get('bahasa') in BAHASA_UCAP else 'tet'
	karakter = KarakterAI.objects.filter(aktif=True, kode=str(d.get('karakter', ''))).first()
	if not ucapan or len(ucapan) > settings.AI['MAKS_TEKS'] or karakter is None:
		return galat('tidak_valid', 400)

	perfil = _perfil(request.user)
	sisa = _batas(perfil) - _terpakai_hari_ini(request.user)
	if sisa <= 0:
		return galat('batas', 429, sisa=0)
	kunci = f'ai-menit:{request.user.pk}'                         # cegah banjir permintaan (biaya token)
	cache.add(kunci, 0, 60)
	if cache.incr(kunci) > settings.AI['BATAS_MENIT']:
		return galat('laju', 429, sisa=sisa)

	sejak = timezone.now() - timedelta(hours=settings.AI['RIWAYAT_JAM'])
	konteks = list(Giliran.objects.filter(user=request.user, karakter=karakter, datetime__gte=sejak).order_by('-datetime')[:settings.AI['RIWAYAT_GILIRAN']])[::-1]
	try:
		h = llm.jawab(karakter, perfil.peran, konteks, ucapan, bahasa)
	except llm.AIGagal:
		return galat('galat', 503, sisa=sisa)                      # gagal: TIDAK dicatat dan TIDAK mengurangi jatah harian

	g = Giliran.objects.create(user=request.user, karakter=karakter, bahasa_ucap=bahasa, ucapan=ucapan, jawab_tet=h.tet, jawab_en=h.en,
	                           koreksi=h.koreksi, gerak=h.gerak, demo=h.demo, model=h.model, token_masuk=h.token_masuk, token_keluar=h.token_keluar)
	return JsonResponse({'ok': True, **_baris(g), 'sisa': sisa - 1})


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
@require_GET
def Riwayat(request):
	k = KarakterAI.objects.filter(kode=request.GET.get('karakter', '')).first()
	qs = Giliran.objects.filter(user=request.user, karakter=k).order_by('-datetime')[:20] if k else []
	return JsonResponse({'riwayat': [_baris(g) for g in list(qs)[::-1]]})


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
@require_POST
def Hapus(request):
	"""User menghapus riwayat percakapannya sendiri."""
	n, _ = Giliran.objects.filter(user=request.user).delete()
	return JsonResponse({'ok': True, 'dihapus': n})
