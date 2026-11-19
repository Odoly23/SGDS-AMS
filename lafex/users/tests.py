from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from config.user_utils import buat_user
from main.tests import user_grup


class DaftarDanAdmin(TestCase):
	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)

	def setUp(self):
		cache.clear()

	def test_daftar_dengan_email_dan_hp(self):
		for kontak, uname in (('Budi@Contoh.com', 'budi@contoh.com'), ('7799 1122', '+67077991122')):
			self.client.logout()
			r = self.client.post('/users/register/', {'kontak': kontak, 'password1': 'rahasia123', 'password2': 'rahasia123'})
			self.assertEqual(r.status_code, 302, kontak)
			u = User.objects.get(username=uname)
			self.assertEqual(u.groups.first().name, 'pelajar')       # akun baru SELALU pelajar; admin yang menaikkan
			self.assertIn('_auth_user_id', self.client.session)

	def test_daftar_ditolak(self):
		buat_user(('email', 'ana@contoh.com'), 'rahasia123')
		kasus = [({'kontak': 'ana@contoh.com', 'password1': 'rahasia123', 'password2': 'rahasia123'}, 'sudah terdaftar'),
		         ({'kontak': 'x@y.com', 'password1': 'rahasia123', 'password2': 'beda12345'}, 'tidak sama'),
		         ({'kontak': 'x@y.com', 'password1': '123', 'password2': '123'}, 'pendek'),
		         ({'kontak': '12345', 'password1': 'rahasia123', 'password2': 'rahasia123'}, 'tidak valid')]
		for data, kata in kasus:
			r = self.client.post('/users/register/', data)
			self.assertEqual(r.status_code, 200, data)
			self.assertContains(r, kata, msg_prefix=str(data))

	def test_hanya_admin_boleh_melihat_dan_mematikan_user(self):
		sasaran = user_grup('nakal', 'pelajar')
		self.client.force_login(user_grup('biasa', 'kontributor'))
		self.client.post(f'/users/toggle/{sasaran.pk}/')
		sasaran.refresh_from_db()
		self.assertTrue(sasaran.is_active)                            # bukan admin: ditolak (halaman 404)
		adm = user_grup('boss', 'admin')
		self.client.force_login(adm)
		self.assertEqual(self.client.get('/users/list/').status_code, 200)
		self.client.post(f'/users/toggle/{sasaran.pk}/')
		sasaran.refresh_from_db()
		self.assertFalse(sasaran.is_active)
		self.client.post(f'/users/toggle/{sasaran.pk}/')
		sasaran.refresh_from_db()
		self.assertTrue(sasaran.is_active)
		self.client.post(f'/users/toggle/{adm.pk}/')                  # tidak bisa mematikan diri sendiri / admin
		adm.refresh_from_db()
		self.assertTrue(adm.is_active)
		self.assertEqual(self.client.get(f'/users/toggle/{sasaran.pk}/').status_code, 405)

	def test_halaman_akun(self):
		self.client.force_login(user_grup('p', 'pelajar'))
		self.assertContains(self.client.get('/users/account/'), 'pelajar')


class AjukanKontributor(TestCase):
	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)

	def setUp(self):
		cache.clear()
		self.p = user_grup('calon', 'pelajar')
		self.adm = user_grup('boss', 'admin')

	def _ajukan(self, **kw):
		d = {'bahasa': 'fataluku', 'alasan': 'Saya penutur asli sejak kecil'}
		d.update(kw)
		return self.client.post('/users/ajukan/', d)

	def test_pelajar_mengajukan_dan_admin_menyetujui(self):
		self.client.force_login(self.p)
		self.assertContains(self.client.get('/users/ajukan/'), 'name="alasan"')
		self.assertContains(self.client.get('/users/account/'), '/users/ajukan/')
		self.assertEqual(self._ajukan().status_code, 302)
		pg = self.p.pengajuan.get()
		self.assertEqual((pg.status, pg.bahasa.kode), ('menunggu', 'fataluku'))
		self.assertNotContains(self.client.get('/users/ajukan/'), 'name="alasan"')                    # sudah ada yang menunggu
		self._ajukan()
		self.assertEqual(self.p.pengajuan.count(), 1)
		self.assertIn('Página não encontrada', self.client.get('/crowdsource/').content.decode())    # belum kontributor
		self.client.force_login(self.adm)
		self.assertContains(self.client.get('/users/pengajuan/'), 'Saya penutur asli')
		self.client.post(f'/users/pengajuan/{pg.pk}/', {'aksi': 'setujui'})
		pg.refresh_from_db()
		self.assertEqual((pg.status, pg.ditinjau_oleh), ('disetujui', self.adm))
		self.assertEqual([g.name for g in self.p.groups.all()], ['kontributor'])                     # satu group
		self.client.force_login(self.p)
		self.assertContains(self.client.get('/crowdsource/'), 'id="cs"')
		self.assertIn('Página não encontrada', self.client.get('/users/ajukan/').content.decode())   # sudah kontributor

	def test_ditolak_boleh_ajukan_lagi_maksimal_tiga(self):
		self.client.force_login(self.p)
		for n in range(3):
			self._ajukan()
			pg = self.p.pengajuan.filter(status='menunggu').get()
			self.client.force_login(self.adm)
			self.client.post(f'/users/pengajuan/{pg.pk}/', {'aksi': 'tolak', 'catatan': 'belum jelas'})
			self.client.force_login(self.p)
		self.assertEqual(self.p.pengajuan.count(), 3)
		self.assertEqual([g.name for g in self.p.groups.all()], ['pelajar'])
		self.assertContains(self.client.get('/users/ajukan/'), 'belum jelas')
		self._ajukan()
		self.assertEqual(self.p.pengajuan.count(), 3)                                                # batas 3

	def test_tamu_dan_input_salah_ditolak(self):
		tamu = user_grup('tamu1', 'pelajar')
		tamu.perfil.is_tamu = True
		tamu.perfil.save()
		self.client.force_login(tamu)
		self._ajukan()
		self.assertEqual(tamu.pengajuan.count(), 0)
		self.client.force_login(self.p)
		for d in ({'bahasa': 'en'}, {'bahasa': 'ngawur'}, {'alasan': 'ok'}):
			self._ajukan(**d)
		self.assertEqual(self.p.pengajuan.count(), 0)

	def test_hanya_admin_meninjau_dan_admin_tidak_diturunkan(self):
		self.client.force_login(self.p)
		self._ajukan()
		pg = self.p.pengajuan.get()
		for u in (self.p, user_grup('kon', 'kontributor')):
			self.client.force_login(u)
			self.assertIn('Página não encontrada', self.client.get('/users/pengajuan/').content.decode())
			self.client.post(f'/users/pengajuan/{pg.pk}/', {'aksi': 'setujui'})
		pg.refresh_from_db()
		self.assertEqual(pg.status, 'menunggu')
		self.client.force_login(self.adm)
		self.assertEqual(self.client.get(f'/users/pengajuan/{pg.pk}/').status_code, 405)
		self.assertEqual(self.client.post(f'/users/pengajuan/{pg.pk}/', {'aksi': 'hapus'}).status_code, 404)
		self.client.post(f'/users/pengajuan/{pg.pk}/', {'aksi': 'tolak'})
		self.client.post(f'/users/pengajuan/{pg.pk}/', {'aksi': 'setujui'})                          # sudah diputuskan: tidak berubah
		pg.refresh_from_db()
		self.assertEqual(pg.status, 'ditolak')
		self.assertEqual([g.name for g in self.p.groups.all()], ['pelajar'])
