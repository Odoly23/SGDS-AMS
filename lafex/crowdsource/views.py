from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Count, Q
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from belajar.models import Kalimat
from config.decorators import allowed_users
from config.user_utils import GRUP_ADMIN, GRUP_KONTRIBUTOR, nama_grup
from ai import suara
from crowdsource.models import RekamanSuara
from crowdsource.utils import TIPE_AUDIO, jenis_audio, tipe_dari_nama
from custom.models import Bahasa, KarakterAI
from users.models import Perfil

BOLEH = [GRUP_KONTRIBUTOR]          # HANYA kontributor yang merekam. Admin tidak merekam: admin meninjau (halaman Tinjau)
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
	"""'Latih AI': hanya group kontributor. Siswa (pelajar) dan admin tidak merekam: tidak ada menu, dan halaman ini menampilkan 404."""
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
	                 mime_type=TIPE_AUDIO[ext], durasi_detik=min(durasi, DURASI_MAKS))
	try:
		r.full_clean()
	except ValidationError:
		return galat('berkas ditolak')
	r.save()
	return JsonResponse({'ok': True, 'total': _total(bahasa), 'bahasa': bahasa.nama})


@login_required
@allowed_users(allowed_roles=BOLEH)
def Kontribusiku(request):
	"""Kontributor melihat hasil kerjanya sendiri: jumlah per status, per bahasa, dan alasan bila ditolak. Tanpa data orang lain."""
	milik = RekamanSuara.objects.filter(pengirim_kode=_kode(request.user))
	hitung = {r['status']: r['n'] for r in milik.values('status').annotate(n=Count('id'))}
	per_bahasa = milik.exclude(status='ditolak').values('bahasa__nama').annotate(n=Count('id')).order_by('-n')
	context = {
		'group': nama_grup(request.user), 'page': 'mine', 'title': 'Ha\'u nia kontribuisaun',
		'total': sum(hitung.values()), 'menunggu': hitung.get('menunggu', 0), 'disetujui': hitung.get('disetujui', 0),
		'ditolak': hitung.get('ditolak', 0), 'per_bahasa': per_bahasa,
		'terakhir': milik.select_related('bahasa', 'kalimat', 'gaya').order_by('-datetime')[:30], 'tts_siap': suara.tts_siap(),
	}
	return render(request, 'crowdsource/kontribusiku.html', context)


# ------------------------------------------------------------------ Tinjau (khusus admin, BUKAN admin Django)
ADMIN = [GRUP_ADMIN]


@login_required
@allowed_users(allowed_roles=ADMIN)
def Tinjau(request):
	"""Admin meninjau rekaman: dengar, setujui/tolak, isi transkripsi, matikan pengirim nakal."""
	status = request.GET.get('status', 'menunggu')
	if status not in ('menunggu', 'disetujui', 'ditolak', 'semua'):
		status = 'menunggu'
	qs = RekamanSuara.objects.select_related('bahasa', 'kalimat', 'gaya')
	if status != 'semua':
		qs = qs.filter(status=status)
	bahasa = request.GET.get('bahasa', '')
	if bahasa:
		qs = qs.filter(bahasa__kode=bahasa)
	hal = Paginator(qs.order_by('datetime'), 15).get_page(request.GET.get('hal'))
	context = {
		'group': nama_grup(request.user), 'page': 'tinjau', 'title': 'Revisaun audio', 'status': status, 'bahasa': bahasa,
		'halaman': hal, 'stt_siap': suara.stt_siap(), 'bahasa_list': Bahasa.objects.filter(rekaman__isnull=False).distinct(),
		'jumlah': {s: RekamanSuara.objects.filter(status=s).count() for s in ('menunggu', 'disetujui', 'ditolak')},
	}
	return render(request, 'crowdsource/tinjau.html', context)


def _whisper(r):
	"""Whisper membuat DRAF transkripsi (belum diperiksa). Return True bila ada teks."""
	with r.audio.open('rb') as f:
		isi = f.read()
	teks = suara.transkripsi(isi, nama=r.audio.name.rsplit('/', 1)[-1], tipe=tipe_dari_nama(r.audio.name))[:1000]
	if not teks:
		return False
	r.transkripsi, r.sumber_transkripsi = teks, 'otomatis'
	r.save(update_fields=['transkripsi', 'sumber_transkripsi'])
	return True


@login_required
@allowed_users(allowed_roles=ADMIN)
@require_POST
def WhisperSemua(request):
	"""Whisper untuk rekaman yang masih menunggu dan belum punya transkripsi (satu batch kecil, supaya tidak menggantung)."""
	if not suara.stt_siap():
		messages.error(request, 'err_stt_off')
		return redirect('crowdsource-tinjau')
	batch = settings.SUARA['WHISPER_BATCH']
	ok = 0
	for r in RekamanSuara.objects.filter(status='menunggu', transkripsi='').order_by('datetime')[:batch]:
		try:
			ok += bool(_whisper(r))
		except suara.SuaraGagal:
			messages.error(request, 'err_stt')
			break
	if ok:
		messages.success(request, 'msg_saved')
	return redirect('crowdsource-tinjau')


def _kembali(request):
	"""Kembali ke daftar (dengan filter yang sama). Hanya alamat dalam halaman Tinjau yang diterima (tanpa open redirect)."""
	tujuan = request.POST.get('kembali', '')
	if tujuan.startswith('/crowdsource/tinjau/') and '//' not in tujuan and '\\' not in tujuan:
		return redirect(tujuan)
	return redirect('crowdsource-tinjau')


@login_required
@allowed_users(allowed_roles=ADMIN)
@require_POST
def TinjauAksi(request, pk):
	r = get_object_or_404(RekamanSuara, pk=pk)
	aksi = request.POST.get('aksi', '')
	if aksi == 'setujui':
		r.tinjau('disetujui', request.user)
	elif aksi == 'tolak':
		r.tinjau('ditolak', request.user, request.POST.get('alasan', '').strip()[:200] or 'Ditolak admin')
	elif aksi == 'transkripsi':
		r.transkripsi = request.POST.get('transkripsi', '').strip()[:1000]
		r.sumber_transkripsi = 'admin' if r.transkripsi else ''          # diperiksa/ditulis admin: boleh dipakai melatih
		r.save(update_fields=['transkripsi', 'sumber_transkripsi'])
	elif aksi == 'whisper':
		if r.sumber_transkripsi == 'admin':
			messages.error(request, 'err_stt_locked')
			return _kembali(request)
		try:
			if not _whisper(r):
				messages.warning(request, 'err_stt_empty')
				return _kembali(request)
		except suara.SuaraGagal:
			messages.error(request, 'err_stt')
			return _kembali(request)
	elif aksi == 'matikan':
		# nonaktifkan akun pengirim (kecuali admin) dan tolak semua rekamannya yang masih menunggu
		ids = Perfil.objects.filter(kode_anonim=r.pengirim_kode).values_list('user_id', flat=True) if r.pengirim_kode else []
		n = User.objects.filter(id__in=ids, is_superuser=False).exclude(groups__name=GRUP_ADMIN).update(is_active=False)
		if r.pengirim_kode:
			RekamanSuara.objects.filter(pengirim_kode=r.pengirim_kode, status='menunggu').update(status='ditolak', alasan_tolak='Pengirim dimatikan')
		messages.warning(request, 'msg_sender_off' if n else 'err_admin_protect')
		return _kembali(request)
	else:
		raise Http404
	messages.success(request, 'msg_saved')
	return _kembali(request)


@login_required
@allowed_users(allowed_roles=ADMIN)
def Audio(request, pk):
	"""Suara hanya bisa didengar admin lewat sini (berkas tidak dibuka umum)."""
	r = get_object_or_404(RekamanSuara, pk=pk)
	if not r.audio:
		raise Http404
	tipe = tipe_dari_nama(r.audio.name)                                 # dari ekstensi hasil validasi isi; mime_type kiriman klien (data lama) diabaikan
	resp = FileResponse(r.audio.open('rb'), content_type=tipe)
	resp['Content-Disposition'] = 'inline; filename="rekaman.' + tipe.split('/')[-1].replace('mpeg', 'mp3') + '"'
	resp['Content-Security-Policy'] = "default-src 'none'; sandbox"        # kalau pun dibuka langsung, tidak ada skrip yang boleh jalan
	return resp


@login_required
@allowed_users(allowed_roles=BOLEH)
@require_POST
def KontribTranskripsi(request, pk):
	"""Kontributor (penutur asli) menulis apa yang ia ucapkan di rekamannya SENDIRI. Yang sudah diperiksa admin terkunci."""
	r = get_object_or_404(RekamanSuara, pk=pk, pengirim_kode=_kode(request.user))
	if r.status == 'ditolak' or r.sumber_transkripsi == 'admin':
		messages.error(request, 'err_tr_locked')
		return redirect('crowdsource-mine')
	r.transkripsi = request.POST.get('transkripsi', '').strip()[:1000]
	r.sumber_transkripsi = 'kontributor' if r.transkripsi else ''
	r.save(update_fields=['transkripsi', 'sumber_transkripsi'])
	messages.success(request, 'msg_saved')
	return redirect('crowdsource-mine')
