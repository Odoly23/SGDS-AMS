import json
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
import hashlib

from django.db.models import Count, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from ai import llm, suara
from ai.models import Giliran
from config.decorators import allowed_users
from config.user_utils import GRUP_ADMIN, SEMUA_GRUP, nama_grup
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


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
@ensure_csrf_cookie
def VideoCall(request):
	"""Layar panggilan LAFEX. TANPA pilihan apa pun: bahasa, topik, dan mode sudah dipilih di halaman Siswa dan datang lewat URL
	(?mode=preman&bahasa=tetun&topik=bebas). Mikrofon menyala otomatis."""
	return render(request, 'ai/video_call.html', {
		'maks_teks': settings.AI['MAKS_TEKS'], 'demo': settings.AI['BACKEND'] == 'dummy', 'xtts': suara.tts_siap(),
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


# ---------------------------------------------------------------- Suara: XTTS (teks -> suara) dan halaman status admin
@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
@require_POST
def Tts(request):
	"""Teks -> suara WAV lewat XTTS milik sendiri. Bila XTTS belum diatur: 503, dan halaman memakai suara bawaan browser."""
	cfg = settings.SUARA
	if not suara.tts_siap():
		return JsonResponse({'ok': False, 'kode': 'mati'}, status=503)
	try:
		teks = str(json.loads(request.body or b'{}').get('teks', '')).strip()
	except ValueError:
		teks = ''
	if not teks or len(teks) > cfg['TTS_MAKS_TEKS']:
		return JsonResponse({'ok': False, 'kode': 'tidak_valid'}, status=400)
	kunci = hashlib.sha256(f"{cfg['TTS_BAHASA']}|{cfg['TTS_SUARA']}|{teks}".encode()).hexdigest()
	audio = cache.get('tts:' + kunci)                                     # kalimat yang sama tidak perlu menghitung ulang di GPU
	if audio is None:
		batas = f'tts-menit:{request.user.pk}'
		cache.add(batas, 0, 60)
		if cache.incr(batas) > cfg['TTS_BATAS_MENIT']:
			return JsonResponse({'ok': False, 'kode': 'laju'}, status=429)
		try:
			audio = suara.sintesis(teks)
		except suara.SuaraGagal:
			return JsonResponse({'ok': False, 'kode': 'galat'}, status=503)
		cache.set('tts:' + kunci, audio, 86400)
	return HttpResponse(audio, content_type='audio/wav')


@login_required
@allowed_users(allowed_roles=[GRUP_ADMIN])
def SuaraAdmin(request):
	"""Admin: status Whisper/XTTS dan kesiapan data latihan per bahasa (hanya yang disetujui + punya transkripsi BUKAN draf Whisper)."""
	from crowdsource.models import RekamanSuara
	cfg = settings.SUARA
	siap = RekamanSuara.objects.filter(status='disetujui').exclude(transkripsi='').exclude(sumber_transkripsi='otomatis')
	per_bahasa = list(siap.values('bahasa__nama').annotate(n=Count('id'), detik=Sum('durasi_detik')).order_by('-n'))
	for b in per_bahasa:
		b['menit'] = round((b['detik'] or 0) / 60, 1)
	context = {
		'group': nama_grup(request.user), 'page': 'tinjau', 'title': 'Suara & Model',
		'stt': {'url': cfg['STT_URL'], 'model': cfg['STT_MODEL'], 'status': suara.cek(cfg['STT_URL'])},
		'tts': {'url': cfg['TTS_URL'], 'bahasa': cfg['TTS_BAHASA'], 'status': suara.cek(cfg['TTS_URL'])},
		'per_bahasa': per_bahasa, 'total_menit': round(sum((b['detik'] or 0) for b in per_bahasa) / 60, 1),
		'draf': RekamanSuara.objects.filter(sumber_transkripsi='otomatis').count(),
		'tanpa': RekamanSuara.objects.filter(status='disetujui', transkripsi='').count(),
	}
	return render(request, 'ai/suara_admin.html', context)
