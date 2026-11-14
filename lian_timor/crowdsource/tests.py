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

from users.models import Perfil

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
		self.assertIn('kontribuidór deit', self.client.get('/crowdsource/').content.decode())    # penjelasan
		self.assertEqual(self._kirim().status_code, 200)                                          # halaman 404 pola SJDF
		self.assertEqual(RekamanSuara.objects.count(), 0)                                         # tapi TIDAK ada rekaman tersimpan
		self.client.force_login(user_grup('a', 'admin'))
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
