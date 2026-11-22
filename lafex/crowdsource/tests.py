import tempfile

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from belajar.models import Kalimat
from crowdsource.models import RekamanSuara
from custom.models import Bahasa, KarakterAI, Level, Materi
from main.tests import user_grup


class Rekaman(TestCase):
	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)
		mt = Materi.objects.create(level=Level.objects.get(nomor=1), judul_tet='m')
		cls.k = Kalimat.objects.create(materi=mt, teks_tet="Bondia, hau hakarak fa'an modo", teks_en='Good morning, I want to sell vegetables')

	def _rekam(self, **kw):
		with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
			return RekamanSuara.objects.create(
				kalimat=self.k, bahasa=Bahasa.objects.get(kode='fataluku'), gaya=KarakterAI.objects.get(kode='sopan'),
				audio=SimpleUploadedFile('nama-asli-orang.webm', b'x' * 100, content_type='audio/webm'), **kw)

	def test_tidak_menyimpan_identitas(self):
		kolom = {f.name for f in RekamanSuara._meta.get_fields()}
		for terlarang in ('nama', 'telepon', 'alamat', 'email', 'user', 'pengguna'):
			self.assertNotIn(terlarang, kolom)
		self.assertFalse(RekamanSuara._meta.get_field('pengirim_kode').is_relation)    # kode samaran, BUKAN relasi ke akun
		r = self._rekam()
		self.assertEqual(r.status, 'menunggu')
		self.assertNotIn('nama-asli-orang', r.audio.name)                              # nama berkas diacak
		self.assertTrue(r.audio.name.startswith('rekaman_suara/fataluku/'))

	def test_batas_ukuran_dan_jenis_berkas(self):
		kw = dict(kalimat=self.k, bahasa=Bahasa.objects.get(kode='fataluku'), gaya=KarakterAI.objects.get(kode='sopan'))
		with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
			with self.assertRaises(ValidationError):
				RekamanSuara(audio=SimpleUploadedFile('b.webm', b'x' * (3 * 1024 * 1024)), **kw).full_clean()
			with self.assertRaises(ValidationError):
				RekamanSuara(audio=SimpleUploadedFile('b.exe', b'x'), **kw).full_clean()

	def test_admin_setujui_tolak_dan_matikan_pengirim(self):
		nakal = user_grup('nakal', 'pelajar')
		adm = User.objects.create_superuser('adm', 'adm@x.com', 'pw12345')
		r = self._rekam(pengirim_kode=nakal.perfil.kode_anonim)
		r.tinjau('disetujui', adm)
		r.refresh_from_db()
		self.assertEqual((r.status, r.ditinjau_oleh), ('disetujui', adm))
		r.tinjau('ditolak', adm, 'bising')
		r.refresh_from_db()
		self.assertEqual(r.alasan_tolak, 'bising')
		self.client.force_login(adm)
		resp = self.client.post('/admin/crowdsource/rekamansuara/', {'action': 'matikan_pengirim', '_selected_action': [r.pk]}, follow=True)
		self.assertEqual(resp.status_code, 200)
		nakal.refresh_from_db()
		self.assertFalse(nakal.is_active)
		adm.refresh_from_db()
		self.assertTrue(adm.is_active)

	def test_halaman_admin_terbuka(self):
		adm = User.objects.create_superuser('adm', 'adm@x.com', 'pw12345')
		self.client.force_login(adm)
		self._rekam()
		for url in ('/admin/', '/admin/auth/user/', '/admin/auth/group/', '/admin/custom/bahasa/', '/admin/custom/level/',
		            '/admin/custom/materi/', '/admin/custom/karakterai/', '/admin/belajar/kalimat/',
		            '/admin/belajar/progresbelajar/', '/admin/crowdsource/rekamansuara/'):
			self.assertEqual(self.client.get(url).status_code, 200, url)
		self.assertEqual(self.client.get('/admin/crowdsource/rekamansuara/add/').status_code, 403)   # suara hanya masuk lewat halaman crowdsource


class Model(TestCase):
	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)

	def test_seed_idempoten_dan_tidak_menimpa_edit_admin(self):
		k = KarakterAI.objects.get(kode='preman')
		k.prompt_sistem = 'diubah admin'
		k.save()
		call_command('seed_awal', verbosity=0)
		self.assertEqual(KarakterAI.objects.get(kode='preman').prompt_sistem, 'diubah admin')
		self.assertEqual((Level.objects.count(), KarakterAI.objects.count()), (5, 3))

	def test_bahasa_aplikasi_dan_daerah(self):
		self.assertEqual(set(Bahasa.objects.filter(jenis='ui').values_list('kode', flat=True)), {'tet', 'en', 'pt', 'id'})
		self.assertTrue(Bahasa.objects.filter(kode='mambae', untuk_crowdsource=True).exists())
		self.assertTrue(Bahasa.objects.filter(kode='tet', untuk_crowdsource=True).exists())
		self.assertTrue(Bahasa.objects.filter(kode='atauru', perlu_verifikasi=True).exists())

	def test_level_materi_kalimat_progres(self):
		from django.db import IntegrityError, transaction
		from belajar.models import ProgresBelajar
		lv = Level.objects.get(nomor=1)
		mt = Materi.objects.create(level=lv, urutan=1, judul_tet='Tawar harga')
		a = Kalimat.objects.create(materi=mt, urutan=1, teks_tet="Ida ne'e hira?", teks_en='How much is this?')
		Kalimat.objects.create(materi=mt, urutan=2, teks_tet='Karun liu.', aktif=False)
		self.assertEqual(lv.total_kalimat, 1)
		self.assertEqual((a.teks('en'), a.teks('pt'), a.level), ('How much is this?', "Ida ne'e hira?", lv))
		u = user_grup('p', 'pelajar')
		ProgresBelajar.objects.create(user=u, kalimat=a)
		with self.assertRaises(IntegrityError), transaction.atomic():
			ProgresBelajar.objects.create(user=u, kalimat=a)

	def test_tiga_karakter_ai(self):
		for k in KarakterAI.objects.all():
			self.assertTrue(k.prompt_sistem and k.nama('en') and k.deskripsi('pt'))
		preman = KarakterAI.objects.get(kode='preman')
		self.assertIn('jangan menghina', preman.prompt_sistem)
		self.assertEqual(preman.contoh_tet, "Woi, modo ne'e fresku los!")


# ======================================================================== halaman & unggah suara
from django.core.cache import cache


WEBM = b'\x1aE\xdf\xa3' + b'\x00' * 60
OGG = b'OggS' + b'\x00' * 60
WAV = b'RIFF\x00\x00\x00\x00WAVEfmt ' + b'\x00' * 40
M4A = b'\x00\x00\x00\x18ftypM4A ' + b'\x00' * 40
MP3 = b'ID3' + b'\x00' * 60


class Unggah(TestCase):
	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)
		call_command('seed_level1', verbosity=0)

	def setUp(self):
		cache.clear()
		self.media = tempfile.mkdtemp()
		self.k = user_grup('kontrib', 'kontributor')
		self.client.force_login(self.k)
		self.kal = Kalimat.objects.filter(materi__level__nomor=1).first()

	def _kirim(self, isi=WEBM, nama='rekaman.webm', **data):
		d = {'kalimat': self.kal.pk, 'bahasa': 'fataluku', 'gaya': 'sopan', 'durasi': '3.2'}
		d.update(data)
		if isi is not None:
			d['audio'] = SimpleUploadedFile(nama, isi, content_type='audio/webm')
		with override_settings(MEDIA_ROOT=self.media):
			return self.client.post('/crowdsource/kirim/', d)

	# ---- group ----
	def test_hanya_kontributor_dan_admin(self):
		self.client.force_login(user_grup('p', 'pelajar'))
		self.assertIn('Página não encontrada', self.client.get('/crowdsource/').content.decode())   # siswa: 404, tanpa halaman penjelasan
		self.assertNotIn('id="cs"', self.client.get('/crowdsource/').content.decode())
		self.assertEqual(self._kirim().status_code, 200)                                          # halaman 404 pola SJDF
		self.assertEqual(RekamanSuara.objects.count(), 0)                                         # tapi TIDAK ada rekaman tersimpan
		self.client.force_login(user_grup('a', 'admin'))                                         # admin tidak merekam, hanya meninjau
		self.assertIn('Página não encontrada', self.client.get('/crowdsource/').content.decode())
		self.assertIn('Página não encontrada', self.client.get('/crowdsource/kontribusiku/').content.decode())
		self.assertEqual(self._kirim().status_code, 200)
		self.assertEqual(RekamanSuara.objects.count(), 0)
		self.client.force_login(self.k)
		self.assertEqual(self._kirim().json()['ok'], True)
		self.client.logout()
		self.assertEqual(self.client.post('/crowdsource/kirim/').status_code, 302)               # belum login

	def test_halaman_menampilkan_bahasa_gaya_dan_penghitung(self):
		self._kirim()
		r = self.client.get('/crowdsource/')
		html = r.content.decode()
		self.assertIn('Fataluku', html)
		self.assertIn('Mambae', html)
		self.assertNotIn('data-kode="en"', html)                         # bahasa aplikasi non-Tetun bukan pilihan bahasa daerah
		self.assertEqual({b.kode: b.n for b in r.context['bahasa_list']}['fataluku'], 1)
		self.assertEqual(len(r.context['gaya_list']), 3)
		self.assertContains(r, 'Dehan fraze ne')                         # petunjuk 4 bahasa
		self.assertContains(r, 'Press the big red button')

	# ---- unggah: berhasil ----
	def test_unggah_berhasil_dan_privasi(self):
		r = self._kirim()
		self.assertEqual(r.json(), {'ok': True, 'total': 1, 'bahasa': 'Fataluku'})
		rek = RekamanSuara.objects.get()
		self.assertEqual((rek.bahasa.kode, rek.gaya.kode, rek.kalimat_id, rek.status), ('fataluku', 'sopan', self.kal.pk, 'menunggu'))
		self.assertEqual(rek.pengirim_kode, self.k.perfil.kode_anonim)
		self.assertTrue(rek.audio.name.startswith('rekaman_suara/fataluku/') and rek.audio.name.endswith('.webm'))
		self.assertNotIn('kontrib', rek.audio.name)                      # tidak ada nama pengguna di jalur berkas
		self.assertEqual(rek.durasi_detik, 3.2)

	def test_semua_format_suara_diterima(self):
		for i, (isi, ext) in enumerate([(WEBM, 'webm'), (OGG, 'ogg'), (WAV, 'wav'), (M4A, 'm4a'), (MP3, 'mp3')]):
			kal = Kalimat.objects.filter(materi__level__nomor=1)[i]
			r = self._kirim(isi, 'x.bin', kalimat=kal.pk)
			self.assertEqual(r.status_code, 200, ext)
			self.assertTrue(RekamanSuara.objects.filter(kalimat=kal).first().audio.name.endswith('.' + ext))

	# ---- unggah: ditolak ----
	def test_berkas_palsu_ditolak_walau_namanya_webm(self):
		for isi in (b'MZ\x90\x00' + b'0' * 50, b'<?php echo 1;', b'GIF89a' + b'0' * 40):
			self.assertEqual(self._kirim(isi, 'malware.webm').status_code, 400)
		self.assertEqual(RekamanSuara.objects.count(), 0)

	def test_kosong_terlalu_besar_dan_terlalu_pendek(self):
		self.assertEqual(self._kirim(None).status_code, 400)
		self.assertEqual(self._kirim(b'').status_code, 400)
		self.assertEqual(self._kirim(WEBM + b'0' * (3 * 1024 * 1024)).status_code, 400)
		for d in ('0.2', 'abc', ''):
			self.assertEqual(self._kirim(durasi=d).status_code, 400, d)
		self.assertEqual(RekamanSuara.objects.count(), 0)

	def test_pilihan_tidak_valid(self):
		self.assertEqual(self._kirim(bahasa='en').status_code, 400)             # en bukan bahasa crowdsource
		self.assertEqual(self._kirim(bahasa='tidak-ada').status_code, 400)
		self.assertEqual(self._kirim(gaya='ngawur').status_code, 400)
		self.assertEqual(self._kirim(kalimat='9999').status_code, 400)
		self.assertEqual(self._kirim(kalimat='abc').status_code, 400)
		Bahasa.objects.filter(kode='fataluku').update(aktif=False)
		self.assertEqual(self._kirim().status_code, 400)
		Bahasa.objects.filter(kode='fataluku').update(aktif=True)
		Kalimat.objects.filter(pk=self.kal.pk).update(untuk_crowdsource=False)
		self.assertEqual(self._kirim().status_code, 400)
		self.assertEqual(RekamanSuara.objects.count(), 0)

	def test_duplikat_ditolak_tapi_gaya_lain_boleh_dan_yang_ditolak_admin_boleh_ulang(self):
		self.assertEqual(self._kirim().status_code, 200)
		self.assertEqual(self._kirim().status_code, 409)                         # bahasa+gaya+kalimat sama
		self.assertEqual(self._kirim(gaya='preman').status_code, 200)            # gaya lain boleh
		RekamanSuara.objects.filter(gaya__kode='sopan').update(status='ditolak')
		self.assertEqual(self._kirim().status_code, 200)                         # yang ditolak admin boleh direkam ulang

	def test_batas_kecepatan(self):
		kode = [self._kirim(kalimat=k.pk).status_code for k in Kalimat.objects.filter(materi__level__nomor=1)[:12]]
		self.assertEqual(kode, [200] * 10 + [429] * 2)
		self.assertEqual(RekamanSuara.objects.count(), 10)

	def test_get_tidak_boleh(self):
		self.assertEqual(self.client.get('/crowdsource/kirim/').status_code, 405)

	# ---- kalimat berikut ----
	def _berikut(self, **q):
		q = {'bahasa': 'fataluku', 'gaya': 'sopan', **q}
		return self.client.get('/crowdsource/berikut/', q)

	def test_berikut_memilih_kalimat_paling_sedikit_direkam_dan_bukan_milik_sendiri(self):
		semua = list(Kalimat.objects.filter(materi__level__nomor=1))
		with override_settings(MEDIA_ROOT=self.media):
			lain = user_grup('lain', 'kontributor')
			for k in semua[:19]:                                              # 19 kalimat sudah direkam orang lain, tinggal 1
				RekamanSuara.objects.create(kalimat=k, bahasa=Bahasa.objects.get(kode='fataluku'), gaya=KarakterAI.objects.get(kode='sopan'),
				                            audio=SimpleUploadedFile('a.webm', WEBM), pengirim_kode=lain.perfil.kode_anonim)
		d = self._berikut().json()
		self.assertEqual(d['kalimat']['id'], semua[19].pk)                    # yang paling sedikit direkam
		self.assertEqual((d['total'], d['bahasa']), (19, 'Fataluku'))
		self.assertIn('en', d['kalimat'])
		self._kirim(kalimat=semua[19].pk)
		d = self._berikut().json()                                            # sisanya sudah direkam orang lain; user ini boleh merekam ulang kalimat lain
		self.assertNotEqual(d['kalimat']['id'], semua[19].pk)                 # tapi bukan yang baru dikirimnya
		with override_settings(MEDIA_ROOT=self.media):                        # 19 kalimat lain direkam sekali lagi (gaya preman) -> semua[19] jadi yang paling sedikit
			for k in semua[:19]:
				RekamanSuara.objects.create(kalimat=k, bahasa=Bahasa.objects.get(kode='fataluku'), gaya=KarakterAI.objects.get(kode='preman'),
				                            audio=SimpleUploadedFile('a.webm', WEBM), pengirim_kode=lain.perfil.kode_anonim)
		self.assertEqual(self._berikut(gaya='preman').json()['kalimat']['id'], semua[19].pk)    # gaya lain: kalimat itu boleh lagi

	def test_berikut_habis_dan_tidak_valid(self):
		Kalimat.objects.update(untuk_crowdsource=False)
		self.assertIsNone(self._berikut().json()['kalimat'])
		self.assertEqual(self._berikut(bahasa='en').status_code, 400)
		self.assertEqual(self._berikut(gaya='x').status_code, 400)
		self.client.force_login(user_grup('p2', 'pelajar'))
		self.assertNotIn('"kalimat"', self._berikut().content.decode())        # pelajar: halaman 404, bukan data

	def test_penghitung_tidak_menghitung_yang_ditolak(self):
		self._kirim()
		self.assertEqual(self._berikut().json()['total'], 1)
		RekamanSuara.objects.update(status='ditolak')
		self.assertEqual(self._berikut().json()['total'], 0)


class TipeKontenAman(Unggah):
	"""Celah XSS tersimpan: Content-Type kiriman klien TIDAK boleh dipakai untuk menyajikan rekaman."""

	def test_mime_klien_diabaikan_saat_simpan_dan_saat_disajikan(self):
		jahat = b'OggS' + b'<script>alert(document.domain)</script>' + b'\x00' * 40      # lolos cek isi "OggS"
		with override_settings(MEDIA_ROOT=self.media):
			resp = self.client.post('/crowdsource/kirim/', {'kalimat': self.kal.pk, 'bahasa': 'fataluku', 'gaya': 'sopan', 'durasi': '3',
			                                                'audio': SimpleUploadedFile('x.ogg', jahat, content_type='text/html')})
			self.assertEqual(resp.status_code, 200)
			r = RekamanSuara.objects.get()
			self.assertEqual(r.mime_type, 'audio/ogg')                                   # ditentukan server dari isi, bukan 'text/html'
			self.client.force_login(user_grup('adm9', 'admin'))
			g = self.client.get(f'/crowdsource/audio/{r.pk}/')
			self.assertEqual(g['Content-Type'], 'audio/ogg')
			self.assertIn('sandbox', g['Content-Security-Policy'])
			self.assertEqual(g['X-Content-Type-Options'], 'nosniff')

	def test_data_lama_berlabel_text_html_tetap_disajikan_sebagai_audio(self):
		with override_settings(MEDIA_ROOT=self.media):
			r = RekamanSuara.objects.create(kalimat=self.kal, bahasa=Bahasa.objects.get(kode='fataluku'), gaya=KarakterAI.objects.get(kode='sopan'),
			                                audio=SimpleUploadedFile('rekaman.webm', WEBM), mime_type='text/html')
			self.client.force_login(user_grup('adm8', 'admin'))
			self.assertEqual(self.client.get(f'/crowdsource/audio/{r.pk}/')['Content-Type'], 'audio/webm')


class KontribusikuDanTinjau(Unggah):
	"""Halaman kontributor 'Kontribusiku' dan halaman admin 'Tinjau' (bukan admin Django)."""

	def setUp(self):
		super().setUp()
		self.adm = user_grup('adm1', 'admin')

	def _buat(self, kontributor, status='menunggu', **kw):
		with override_settings(MEDIA_ROOT=self.media):
			return RekamanSuara.objects.create(
				kalimat=self.kal, bahasa=Bahasa.objects.get(kode='fataluku'), gaya=KarakterAI.objects.get(kode='sopan'), status=status,
				audio=SimpleUploadedFile('x.webm', WEBM, content_type='audio/webm'), pengirim_kode=kontributor.perfil.kode_anonim, **kw)

	def test_kontribusiku_hanya_milik_sendiri_dan_tanpa_data_pribadi(self):
		lain = user_grup('orang-lain', 'kontributor')
		self._buat(self.k, 'disetujui')
		self._buat(self.k, 'ditolak', alasan_tolak='terlalu bising')
		self._buat(self.k)
		self._buat(lain)
		r = self.client.get('/crowdsource/kontribusiku/')
		self.assertEqual((r.context['total'], r.context['disetujui'], r.context['ditolak'], r.context['menunggu']), (3, 1, 1, 1))
		html = r.content.decode()
		self.assertIn('terlalu bising', html)
		self.assertNotIn('orang-lain', html)
		self.assertNotIn(lain.perfil.kode_anonim, html)
		self.assertNotIn('<audio', html)

	def test_pelajar_dan_anonim_tidak_boleh(self):
		self.client.force_login(user_grup('p', 'pelajar'))
		for u in ('/crowdsource/kontribusiku/', '/crowdsource/tinjau/', '/crowdsource/audio/1/'):
			self.assertIn('Página não encontrada', self.client.get(u).content.decode(), u)
		self.client.logout()
		self.assertEqual(self.client.get('/crowdsource/tinjau/').status_code, 302)

	def test_kontributor_tidak_boleh_meninjau(self):
		r = self._buat(self.k)
		for url, method in (('/crowdsource/tinjau/', 'get'), (f'/crowdsource/audio/{r.pk}/', 'get')):
			self.assertIn('Página não encontrada', getattr(self.client, method)(url).content.decode())
		self.client.post(f'/crowdsource/tinjau/{r.pk}/', {'aksi': 'setujui'})
		r.refresh_from_db()
		self.assertEqual(r.status, 'menunggu')

	def test_admin_melihat_dan_memfilter(self):
		a = self._buat(self.k)
		self._buat(self.k, 'disetujui')
		self.client.force_login(self.adm)
		r = self.client.get('/crowdsource/tinjau/')
		self.assertEqual([x.pk for x in r.context['halaman']], [a.pk])
		self.assertContains(r, f'/crowdsource/audio/{a.pk}/')
		self.assertEqual(len(self.client.get('/crowdsource/tinjau/?status=semua').context['halaman']), 2)
		self.assertEqual(len(self.client.get('/crowdsource/tinjau/?status=ngawur').context['halaman']), 1)   # nilai tak dikenal -> menunggu
		self.assertNotContains(r, self.k.perfil.kode_anonim)                                                  # kode samaran tidak ditampilkan

	def test_admin_setujui_tolak_transkripsi(self):
		r = self._buat(self.k)
		self.client.force_login(self.adm)
		self.client.post(f'/crowdsource/tinjau/{r.pk}/', {'aksi': 'transkripsi', 'transkripsi': 'bondia'})
		self.client.post(f'/crowdsource/tinjau/{r.pk}/', {'aksi': 'setujui'})
		r.refresh_from_db()
		self.assertEqual((r.status, r.transkripsi, r.ditinjau_oleh), ('disetujui', 'bondia', self.adm))
		self.client.post(f'/crowdsource/tinjau/{r.pk}/', {'aksi': 'tolak', 'alasan': 'bising'})
		r.refresh_from_db()
		self.assertEqual((r.status, r.alasan_tolak), ('ditolak', 'bising'))
		self.assertEqual(self.client.post(f'/crowdsource/tinjau/{r.pk}/', {'aksi': 'hapus'}).status_code, 404)
		self.assertEqual(self.client.get(f'/crowdsource/tinjau/{r.pk}/').status_code, 405)

	def test_matikan_pengirim_tolak_yang_menunggu_dan_admin_aman(self):
		a = self._buat(self.k)
		b = self._buat(self.k)
		self.client.force_login(self.adm)
		self.client.post(f'/crowdsource/tinjau/{a.pk}/', {'aksi': 'matikan'})
		self.k.refresh_from_db()
		self.assertFalse(self.k.is_active)
		b.refresh_from_db()
		self.assertEqual((b.status, b.alasan_tolak), ('ditolak', 'Pengirim dimatikan'))
		adm2 = user_grup('adm2', 'admin')
		c = self._buat(adm2)
		self.client.post(f'/crowdsource/tinjau/{c.pk}/', {'aksi': 'matikan'})
		adm2.refresh_from_db()
		self.assertTrue(adm2.is_active)                                                                     # admin tidak bisa dimatikan

	def test_audio_hanya_admin_dan_tidak_ada_open_redirect(self):
		r = self._buat(self.k)
		self.client.force_login(self.adm)
		with override_settings(MEDIA_ROOT=self.media):
			resp = self.client.get(f'/crowdsource/audio/{r.pk}/')
			self.assertEqual(resp.status_code, 200)
			self.assertEqual(b''.join(resp.streaming_content), WEBM)
		for tujuan in ('https://jahat.example/', '//jahat.example/', '/crowdsource/tinjau//jahat.example'):
			resp = self.client.post(f'/crowdsource/tinjau/{r.pk}/', {'aksi': 'transkripsi', 'transkripsi': 'x', 'kembali': tujuan})
			self.assertEqual(resp['Location'], '/crowdsource/tinjau/', tujuan)
		resp = self.client.post(f'/crowdsource/tinjau/{r.pk}/', {'aksi': 'transkripsi', 'transkripsi': 'x', 'kembali': '/crowdsource/tinjau/?status=semua'})
		self.assertEqual(resp['Location'], '/crowdsource/tinjau/?status=semua')


import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from django.conf import settings
from django.core.cache import cache

from ai import suara


class ServerSuaraPalsu(BaseHTTPRequestHandler):
	"""Meniru Whisper (/audio/transcriptions) dan XTTS (/tts) lewat HTTP sungguhan di localhost."""
	catatan = []

	def log_message(self, *a):
		pass

	def do_POST(self):
		isi = self.rfile.read(int(self.headers.get('Content-Length', 0)))
		ServerSuaraPalsu.catatan.append((self.path, self.headers.get('Content-Type', ''), isi))
		if self.path.endswith('/audio/transcriptions'):
			if b'RUSAK' in isi:
				self.send_response(500); self.end_headers(); return
			teks = '' if b'HENING' in isi else 'bondia ha u naran Ana'
			self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
			self.wfile.write(json.dumps({'text': teks}).encode())
		elif self.path == '/tts':
			self.send_response(200); self.send_header('Content-Type', 'audio/wav'); self.end_headers()
			self.wfile.write(b'RIFF' + b'\x00' * 40)
		else:
			self.send_response(404); self.end_headers()

	def do_GET(self):
		self.send_response(200); self.end_headers()


class Suara(Unggah):
	"""Whisper (draf transkripsi), XTTS (contoh suara), halaman admin, ekspor data latihan."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.srv = HTTPServer(('127.0.0.1', 0), ServerSuaraPalsu)
		threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
		cls.url = f'http://127.0.0.1:{cls.srv.server_port}'

	@classmethod
	def tearDownClass(cls):
		cls.srv.shutdown(); cls.srv.server_close()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		ServerSuaraPalsu.catatan.clear()
		self.adm = user_grup('adm1', 'admin')
		self.cfg = override_settings(SUARA={**settings.SUARA, 'STT_URL': self.url, 'TTS_URL': self.url + '/tts'}, MEDIA_ROOT=self.media)
		self.cfg.enable()

	def tearDown(self):
		self.cfg.disable()

	def _buat(self, isi=WEBM, status='menunggu', **kw):
		return RekamanSuara.objects.create(
			kalimat=self.kal, bahasa=Bahasa.objects.get(kode='fataluku'), gaya=KarakterAI.objects.get(kode='sopan'), status=status, durasi_detik=3.0,
			audio=SimpleUploadedFile('x.webm', isi, content_type='audio/webm'), pengirim_kode=self.k.perfil.kode_anonim, **kw)

	# ---- klien ----
	def test_klien_whisper_dan_xtts_lewat_http_sungguhan(self):
		self.assertEqual(suara.transkripsi(WEBM), 'bondia ha u naran Ana')
		path, ctype, isi = ServerSuaraPalsu.catatan[-1]
		self.assertTrue(ctype.startswith('multipart/form-data; boundary='))
		self.assertIn(b'name="model"', isi); self.assertIn(WEBM, isi)
		self.assertEqual(suara.sintesis('Bondia')[:4], b'RIFF')
		self.assertEqual(suara.cek(self.url), 'hidup')
		self.assertEqual(suara.cek(''), 'belum diatur')
		self.assertEqual(suara.cek('http://127.0.0.1:1'), 'mati')

	def test_klien_mati_atau_belum_diatur(self):
		with override_settings(SUARA={**settings.SUARA, 'STT_URL': '', 'TTS_URL': ''}):
			for f in (lambda: suara.transkripsi(WEBM), lambda: suara.sintesis('x')):
				with self.assertRaises(suara.SuaraGagal):
					f()
		with override_settings(SUARA={**settings.SUARA, 'STT_URL': 'http://127.0.0.1:1', 'TTS_URL': 'http://127.0.0.1:1/x'}):
			for f in (lambda: suara.transkripsi(WEBM), lambda: suara.sintesis('x')):
				with self.assertRaises(suara.SuaraGagal):
					f()

	# ---- admin: Whisper di halaman Tinjau ----
	def test_whisper_membuat_draf_dan_admin_memeriksanya(self):
		r = self._buat()
		self.client.force_login(self.adm)
		self.assertContains(self.client.get('/crowdsource/tinjau/'), 'name="aksi" value="whisper"')
		self.client.post(f'/crowdsource/tinjau/{r.pk}/', {'aksi': 'whisper'})
		r.refresh_from_db()
		self.assertEqual((r.transkripsi, r.sumber_transkripsi), ('bondia ha u naran Ana', 'otomatis'))
		self.assertContains(self.client.get('/crowdsource/tinjau/'), 'Draf Whisper')
		self.client.post(f'/crowdsource/tinjau/{r.pk}/', {'aksi': 'transkripsi', 'transkripsi': "Bondia, ha'u naran Ana"})
		r.refresh_from_db()
		self.assertEqual(r.sumber_transkripsi, 'admin')                         # ditulis/diperiksa manusia
		self.client.post(f'/crowdsource/tinjau/{r.pk}/', {'aksi': 'whisper'})   # tidak boleh menimpa yang sudah diperiksa
		r.refresh_from_db()
		self.assertEqual((r.transkripsi, r.sumber_transkripsi), ("Bondia, ha'u naran Ana", 'admin'))

	def test_whisper_gagal_atau_hening_tidak_mengubah_apa_pun(self):
		bisu, rusak = self._buat(isi=WEBM + b'HENING'), self._buat(isi=WEBM + b'RUSAK')
		self.client.force_login(self.adm)
		for r in (bisu, rusak):
			self.client.post(f'/crowdsource/tinjau/{r.pk}/', {'aksi': 'whisper'})
			r.refresh_from_db()
			self.assertEqual((r.transkripsi, r.sumber_transkripsi), ('', ''))
		with override_settings(SUARA={**settings.SUARA, 'STT_URL': ''}):
			self.assertNotContains(self.client.get('/crowdsource/tinjau/'), 'value="whisper"')
			self.assertEqual(self.client.post('/crowdsource/tinjau/whisper-semua/').status_code, 302)

	def test_whisper_semua_hanya_yang_menunggu_dan_belum_ada_teks(self):
		a, b = self._buat(), self._buat(status='disetujui')
		c = self._buat(transkripsi='sudah ada', sumber_transkripsi='kontributor')
		self.client.force_login(self.adm)
		self.client.post('/crowdsource/tinjau/whisper-semua/')
		for r in (a, b, c):
			r.refresh_from_db()
		self.assertEqual([a.sumber_transkripsi, b.sumber_transkripsi, c.sumber_transkripsi], ['otomatis', '', 'kontributor'])
		self.client.force_login(self.k)
		self.client.post('/crowdsource/tinjau/whisper-semua/')                  # bukan admin: tidak ada efek
		self.assertEqual(len(ServerSuaraPalsu.catatan), 1)

	# ---- kontributor menulis ucapannya sendiri ----
	def test_kontributor_menulis_transkripsi_miliknya_saja(self):
		r = self._buat()
		lain = user_grup('lain', 'kontributor')
		self.assertContains(self.client.get('/crowdsource/kontribusiku/'), f'/crowdsource/kontribusiku/{r.pk}/transkripsi/')
		self.client.post(f'/crowdsource/kontribusiku/{r.pk}/transkripsi/', {'transkripsi': 'Bondia dia'})
		r.refresh_from_db()
		self.assertEqual((r.transkripsi, r.sumber_transkripsi), ('Bondia dia', 'kontributor'))
		self.client.force_login(lain)
		self.assertEqual(self.client.post(f'/crowdsource/kontribusiku/{r.pk}/transkripsi/', {'transkripsi': 'curang'}).status_code, 404)
		self.client.force_login(self.k)
		self.client.post(f'/crowdsource/kontribusiku/{r.pk}/transkripsi/', {'transkripsi': ''})        # menghapus
		r.refresh_from_db()
		self.assertEqual((r.transkripsi, r.sumber_transkripsi), ('', ''))
		r.transkripsi, r.sumber_transkripsi = 'diperiksa', 'admin'; r.save()
		self.client.post(f'/crowdsource/kontribusiku/{r.pk}/transkripsi/', {'transkripsi': 'ubah'})   # terkunci setelah diperiksa admin
		r.refresh_from_db()
		self.assertEqual(r.transkripsi, 'diperiksa')
		self.client.force_login(user_grup('p', 'pelajar'))
		self.assertIn('Página não encontrada', self.client.post(f'/crowdsource/kontribusiku/{r.pk}/transkripsi/', {'transkripsi': 'x'}).content.decode())

	# ---- XTTS ----
	def test_tts_mengembalikan_wav_memakai_cache_dan_dibatasi(self):
		def tts(teks='Bondia'):
			return self.client.post('/ai/tts/', json.dumps({'teks': teks}), content_type='application/json')
		r = tts()
		self.assertEqual((r.status_code, r['Content-Type'], r.content[:4]), (200, 'audio/wav', b'RIFF'))
		tts()
		self.assertEqual(len([c for c in ServerSuaraPalsu.catatan if c[0] == '/tts']), 1)    # kalimat sama: dari cache, GPU tidak dipakai lagi
		self.assertEqual(tts('').status_code, 400)
		self.assertEqual(tts('x' * 301).status_code, 400)
		with override_settings(SUARA={**settings.SUARA, 'TTS_URL': ''}):
			self.assertEqual(tts().status_code, 503)                                        # halaman lalu memakai suara browser
		with override_settings(SUARA={**settings.SUARA, 'TTS_BATAS_MENIT': 2}):
			cache.clear()
			self.assertEqual([tts(f'k{i}').status_code for i in range(3)], [200, 200, 429])
		self.client.logout()
		self.assertEqual(tts().status_code, 302)

	def test_halaman_video_call_dan_rekam_tahu_xtts(self):
		self.assertContains(self.client.get('/video-call/'), 'data-xtts="1"')
		self.assertContains(self.client.get('/crowdsource/'), 'data-tts="/ai/tts/"')
		with override_settings(SUARA={**settings.SUARA, 'TTS_URL': ''}):
			self.assertContains(self.client.get('/video-call/'), 'data-xtts="0"')

	# ---- halaman admin Suara & Model + ekspor ----
	def test_halaman_suara_admin_dan_hak_akses(self):
		self._buat(status='disetujui', transkripsi='Bondia', sumber_transkripsi='admin')
		self._buat(status='disetujui', transkripsi='draf', sumber_transkripsi='otomatis')
		self.client.force_login(self.adm)
		r = self.client.get('/ai/suara/')
		self.assertEqual((r.context['stt']['status'], r.context['tts']['status'], r.context['draf']), ('hidup', 'hidup', 1))
		self.assertEqual(r.context['per_bahasa'][0]['n'], 1)                                # draf Whisper tidak dihitung sebagai data latihan
		for u in (self.k, user_grup('p', 'pelajar')):
			self.client.force_login(u)
			self.assertIn('Página não encontrada', self.client.get('/ai/suara/').content.decode())

	def test_ekspor_hanya_disetujui_dan_bukan_draf_tanpa_data_pribadi(self):
		import shutil
		import subprocess
		import tempfile
		if not shutil.which('ffmpeg'):
			self.skipTest('ffmpeg tidak ada')
		wav = os.path.join(self.media, 'asli.wav')
		subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', wav], check=True)
		isi = open(wav, 'rb').read()
		baik = self._buat(isi=isi, status='disetujui', transkripsi='Bondia | dia', sumber_transkripsi='kontributor')
		self._buat(isi=isi, status='disetujui', transkripsi='draf', sumber_transkripsi='otomatis')
		self._buat(isi=isi, status='menunggu', transkripsi='belum', sumber_transkripsi='admin')
		self._buat(isi=isi, status='ditolak', transkripsi='tolak', sumber_transkripsi='admin')
		out = tempfile.mkdtemp()
		call_command('export_suara', out=out, bahasa='fataluku', stdout=mock_stdout())
		baris = [json.loads(b) for b in open(os.path.join(out, 'whisper', 'train.jsonl'), encoding='utf-8')]
		self.assertEqual([(b['audio'], b['text']) for b in baris], [(f'wavs/r{baik.pk}.wav', 'Bondia dia')])
		meta = open(os.path.join(out, 'xtts', 'metadata.csv'), encoding='utf-8').read().splitlines()
		self.assertEqual(meta, ['audio_file|text|speaker_name', f'wavs/r{baik.pk}.wav|Bondia dia|lafex'])
		self.assertTrue(os.path.exists(os.path.join(out, 'whisper', 'wavs', f'r{baik.pk}.wav')))
		self.assertTrue(os.path.exists(os.path.join(out, 'xtts', 'wavs', f'r{baik.pk}.wav')))
		for berkas in (os.path.join(out, 'whisper', 'train.jsonl'), os.path.join(out, 'xtts', 'metadata.csv')):
			self.assertNotIn(self.k.perfil.kode_anonim, open(berkas, encoding='utf-8').read())     # tanpa kode pengirim


def mock_stdout():
	import io
	return io.StringIO()
