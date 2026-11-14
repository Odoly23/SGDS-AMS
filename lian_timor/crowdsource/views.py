from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from belajar.models import Kalimat
from config.decorators import allowed_users
from config.user_utils import GRUP_ADMIN, GRUP_KONTRIBUTOR, nama_grup
from crowdsource.models import RekamanSuara
from crowdsource.utils import jenis_audio
from custom.models import Bahasa, KarakterAI
from users.models import Perfil

BOLEH = [GRUP_ADMIN, GRUP_KONTRIBUTOR]          # hanya group kontributor (dan admin)
MAKS_PER_MENIT, MAKS_PER_HARI = 10, 100
DURASI_MIN, DURASI_MAKS = 0.8, 120.0


def _bahasa_aktif():
	return Bahasa.objects.filter(aktif=True, untuk_crowdsource=True)


def _total(bahasa):
	"""Jumlah suara terkumpul untuk satu bahasa (yang ditolak tidak dihitung)."""
	return RekamanSuara.objects.filter(bahasa=bahasa).exclude(status='ditolak').count()


def _kode(user):
	return Perfil.objects.get_or_create(user=user)[0].kode_anonim


def _kalimat_boleh():
	return Kalimat.objects.filter(aktif=True, untuk_crowdsource=True, materi__aktif=True, materi__level__aktif=True)


@login_required
@allowed_users(allowed_roles=BOLEH)
def CrowdsourceHome(request):
	"""'Latih AI': hanya group kontributor dan admin. Siswa (pelajar) tidak perlu: tidak ada menu, dan halaman ini menampilkan 404."""
	context = {
		'group': nama_grup(request.user), 'page': 'crowdsource', 'title': 'Ajuda AI',
		'bahasa_list': _bahasa_aktif().annotate(n=Count('rekaman', filter=~Q(rekaman__status='ditolak'))),
		'gaya_list': KarakterAI.objects.filter(aktif=True),
	}
	return render(request, 'crowdsource/crowdsource.html', context)


@login_required
@allowed_users(allowed_roles=BOLEH)
@require_GET
def Berikut(request):
	"""Satu kalimat untuk direkam: yang PALING SEDIKIT direkam di bahasa itu, dan belum pernah direkam user ini (bahasa+gaya sama)."""
	bahasa = _bahasa_aktif().filter(kode=request.GET.get('bahasa', '')).first()
	gaya = KarakterAI.objects.filter(aktif=True, kode=request.GET.get('gaya', '')).first()
	if not bahasa or not gaya:
		return JsonResponse({'detail': 'pilihan tidak valid'}, status=400)
	sudah = RekamanSuara.objects.filter(bahasa=bahasa, gaya=gaya, pengirim_kode=_kode(request.user)).values('kalimat_id')
	k = (_kalimat_boleh().exclude(id__in=sudah)
	     .annotate(n=Count('rekaman', filter=Q(rekaman__bahasa=bahasa) & ~Q(rekaman__status='ditolak')))
	     .order_by('n', '?').first())
	kalimat = None
	if k:
		kalimat = {'id': k.id, 'emoji': k.emoji, 'tet': k.teks_tet, 'en': k.teks_en, 'pt': k.teks_pt, 'id_': k.teks_id}
	return JsonResponse({'kalimat': kalimat, 'total': _total(bahasa), 'bahasa': bahasa.nama})


@login_required
@allowed_users(allowed_roles=BOLEH)
@require_POST
def Kirim(request):
	"""Terima rekaman. Disimpan HANYA: bahasa, kalimat, gaya bicara, file suara (+ kode acak pengirim untuk memblokir penyalahgunaan)."""
	def galat(pesan, status=400):
		return JsonResponse({'ok': False, 'detail': pesan}, status=status)

	# batas kecepatan per user (melindungi penyimpanan & Admin dari banjir berkas)
	pk, hari = request.user.pk, timezone.localdate().isoformat()
	for kunci, batas, jeda in ((f'cs-menit:{pk}', MAKS_PER_MENIT, 60), (f'cs-hari:{pk}:{hari}', MAKS_PER_HARI, 86400)):
		cache.add(kunci, 0, jeda)
		if cache.incr(kunci) > batas:
			return galat('terlalu cepat', 429)

	bahasa = _bahasa_aktif().filter(kode=request.POST.get('bahasa', '')).first()
	gaya = KarakterAI.objects.filter(aktif=True, kode=request.POST.get('gaya', '')).first()
	kalimat = _kalimat_boleh().filter(id=request.POST.get('kalimat') or 0).first() if str(request.POST.get('kalimat', '')).isdigit() else None
	if not (bahasa and gaya and kalimat):
		return galat('pilihan tidak valid')

	berkas = request.FILES.get('audio')
	if berkas is None or not 0 < berkas.size <= settings.SUARA_MAKS_BYTE:
		return galat('berkas suara kosong atau terlalu besar')
	ext = jenis_audio(berkas.read(16))
	berkas.seek(0)
	if ext is None:
		return galat('berkas bukan suara yang didukung')
	try:
		durasi = float(request.POST.get('durasi', ''))
	except ValueError:
		durasi = None
	if durasi is None or durasi < DURASI_MIN:
		return galat('terlalu pendek')
	kode = _kode(request.user)
	if RekamanSuara.objects.filter(kalimat=kalimat, bahasa=bahasa, gaya=gaya, pengirim_kode=kode).exclude(status='ditolak').exists():
		return galat('sudah dikirim', 409)

	berkas.name = f'rekaman.{ext}'
	r = RekamanSuara(kalimat=kalimat, bahasa=bahasa, gaya=gaya, audio=berkas, pengirim_kode=kode,
	                 mime_type=(berkas.content_type or '').split(';')[0][:40], durasi_detik=min(durasi, DURASI_MAKS))
	try:
		r.full_clean()
	except ValidationError:
		return galat('berkas ditolak')
	r.save()
	return JsonResponse({'ok': True, 'total': _total(bahasa), 'bahasa': bahasa.nama})
