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
