import json
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
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


class GiliranGagal(Exception):
	"""Giliran tidak bisa diproses (kode: tidak_valid | batas | laju | galat)."""

	def __init__(self, kode, status, **ekstra):
		self.kode, self.status, self.ekstra = kode, status, ekstra


def proses_giliran(user, karakter, ucapan, bahasa, tambahan=''):
	"""Satu giliran AI: batas harian, batas per menit, konteks, panggil model, catat. Dipakai Bicara (chat) dan LafexChat (video call),
	sehingga jatah harian dan perlindungan biaya SAMA. Return (Giliran, sisa)."""
	if not ucapan or len(ucapan) > settings.AI['MAKS_TEKS'] or karakter is None:
		raise GiliranGagal('tidak_valid', 400)
	perfil = _perfil(user)
	sisa = _batas(perfil) - _terpakai_hari_ini(user)
	if sisa <= 0:
		raise GiliranGagal('batas', 429, sisa=0)
	kunci = f'ai-menit:{user.pk}'                                  # cegah banjir permintaan (biaya token)
	cache.add(kunci, 0, 60)
	if cache.incr(kunci) > settings.AI['BATAS_MENIT']:
		raise GiliranGagal('laju', 429, sisa=sisa)

	sejak = timezone.now() - timedelta(hours=settings.AI['RIWAYAT_JAM'])
	konteks = list(Giliran.objects.filter(user=user, karakter=karakter, datetime__gte=sejak).order_by('-datetime')[:settings.AI['RIWAYAT_GILIRAN']])[::-1]
	try:
		h = llm.jawab(karakter, perfil.peran, konteks, ucapan, bahasa, tambahan)
	except llm.AIGagal:
		raise GiliranGagal('galat', 503, sisa=sisa)               # gagal: TIDAK dicatat dan TIDAK mengurangi jatah harian
	g = Giliran.objects.create(user=user, karakter=karakter, bahasa_ucap=bahasa, ucapan=ucapan, jawab_tet=h.tet, jawab_en=h.en,
	                           koreksi=h.koreksi, gerak=h.gerak, demo=h.demo, model=h.model, token_masuk=h.token_masuk, token_keluar=h.token_keluar)
	return g, sisa - 1


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
@require_POST
def Bicara(request):
	"""Satu giliran: terima teks ucapan -> jawaban AI (Tetun + Inggris + koreksi)."""
	try:
		d = json.loads(request.body or b'{}')
	except ValueError:
		return JsonResponse({'ok': False, 'kode': 'tidak_valid'}, status=400)
	bahasa = d.get('bahasa') if d.get('bahasa') in BAHASA_UCAP else 'tet'
	karakter = KarakterAI.objects.filter(aktif=True, kode=str(d.get('karakter', ''))).first()
	try:
		g, sisa = proses_giliran(request.user, karakter, str(d.get('teks', '')).strip(), bahasa)
	except GiliranGagal as e:
		return JsonResponse({'ok': False, 'kode': e.kode, **e.ekstra}, status=e.status)
	return JsonResponse({'ok': True, **_baris(g), 'sisa': sisa})


# ---------------------------------------------------------------- Video call (panggilan suara dengan LAFEX)
# Mode panggilan -> karakter yang sudah ada + tambahan perintah. Tambahan ditulis di SERVER, bukan diterima dari browser.
MODE_PANGGILAN = {
	'preman': ('preman', "MODE PANGGILAN: bicara gaul dan santai, seperti teman. Tetap sopan, tidak kasar."),
	'pintar': ('sopan', "MODE PANGGILAN: guru yang sabar. Betulkan kesalahan SATU per SATU (yang terpenting dulu), beri kalimat yang benar, "
	                    "lalu ajak pengguna mengulangnya."),
	'professional': ('profesional', "MODE PANGGILAN: formal dan profesional, seperti latihan wawancara kerja. Bahasa baku, sopan, jelas."),
}
BAHASA_VC = {'tetun': 'tet', 'portugues': 'pt', 'inggris': 'en', 'indonesia': 'id'}
MENIT_BAWAAN, MENIT_MAKS = 5, 15


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
@ensure_csrf_cookie
def VideoCall(request):
	"""Halaman panggilan: bicara langsung dengan LAFEX, tangan bebas, sampai waktu habis. Mode/bahasa/topik/menit dari URL."""
	return render(request, 'ai/video_call.html', {
		'maks_teks': settings.AI['MAKS_TEKS'], 'demo': settings.AI['BACKEND'] == 'dummy',
		'menit_bawaan': MENIT_BAWAAN, 'menit_maks': MENIT_MAKS,
	})


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
@require_POST
def LafexChat(request):
	"""API panggilan: {pesan, mode, bahasa, topik} -> {ok, jawaban, terjemahan, koreksi, gerak, benar, lang, sisa}."""
	try:
		d = json.loads(request.body or b'{}')
	except ValueError:
		return JsonResponse({'ok': False, 'kode': 'tidak_valid'}, status=400)
	kode_karakter, tambahan = MODE_PANGGILAN.get(d.get('mode'), MODE_PANGGILAN['preman'])
	bahasa_vc = d.get('bahasa') if d.get('bahasa') in BAHASA_VC else 'tetun'
	topik = re.sub(r'[^\w\- ]', '', str(d.get('topik', '')))[:40].strip()
	if topik and topik != 'bebas':
		tambahan += f' Topik latihan: {topik}.'
	karakter = KarakterAI.objects.filter(aktif=True, kode=kode_karakter).first()
	try:
		g, sisa = proses_giliran(request.user, karakter, str(d.get('pesan', '')).strip(), BAHASA_VC[bahasa_vc], tambahan)
	except GiliranGagal as e:
		return JsonResponse({'ok': False, 'kode': e.kode, **e.ekstra}, status=e.status)
	return JsonResponse({'ok': True, 'jawaban': g.jawab_tet, 'terjemahan': g.jawab_en, 'koreksi': g.koreksi, 'gerak': g.gerak,
	                     'benar': not g.koreksi, 'lang': 'tetun', 'demo': g.demo, 'sisa': sisa})


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
