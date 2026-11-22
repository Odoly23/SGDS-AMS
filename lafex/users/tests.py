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


class Naran(TestCase):
	"""Kolom Naran di form daftar dan halaman Akun; email tanpa nama -> first_name & last_name dibuat otomatis, terpisah."""

	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)

	def setUp(self):
		cache.clear()

	def _daftar(self, kontak, naran=None, ip='203.0.113.1'):
		self.client.logout()
		d = {'kontak': kontak, 'password1': 'rahasia123', 'password2': 'rahasia123'}
		if naran is not None:
			d['naran'] = naran
		return self.client.post('/users/register/', d, REMOTE_ADDR=ip)

	def test_helper_pisah_dan_rapikan(self):
		from config.user_utils import naran_dari_email, naran_valid, pisah_naran, rapikan_naran
		self.assertEqual(rapikan_naran('  vicente   SOUSA '), 'Vicente Sousa')
		self.assertEqual(rapikan_naran('maria da costa'), 'Maria da Costa')
		self.assertEqual(rapikan_naran('João McDonald'), 'João McDonald')                       # campur besar-kecil dibiarkan
		self.assertEqual(pisah_naran('maria da costa'), ('Maria', 'da Costa'))                  # sisanya jadi last_name
		self.assertEqual(pisah_naran('Ana'), ('Ana', ''))
		self.assertEqual(pisah_naran(''), ('', ''))
		self.assertEqual(naran_dari_email('vicente.sousa@gmail.com'), 'Vicente Sousa')
		self.assertEqual(naran_dari_email('ana_maria99@x.com'), 'Ana Maria')
		self.assertEqual(naran_dari_email('joao123@x.com'), 'Joao')
		for bukan in ('info@x.com', 'admin.lafex@x.com', '12345@x.com', 'a@x.com', '+67077123456', ''):
			self.assertEqual(naran_dari_email(bukan), '', bukan)
		for ok in ("Maria da Costa", "D'Avila", "José-Maria", "Ana"):
			self.assertTrue(naran_valid(ok), ok)
		for jelek in ('A', 'x' * 61, 'Ana123', '<b>Ana</b>', 'Ana_Maria', '12', '-Ana', ''):
			self.assertFalse(naran_valid(jelek), jelek)

	def test_daftar_dengan_naran_diisi_pengguna(self):
		self.assertEqual(self._daftar('maria@x.com', 'maria da costa').status_code, 302)
		u = User.objects.get(username='maria@x.com')
		self.assertEqual((u.first_name, u.last_name), ('Maria', 'da Costa'))                    # terpisah, bukan dari email

	def test_daftar_email_tanpa_naran_dibuat_dari_email(self):
		self._daftar('vicente.sousa@x.com', '')
		u = User.objects.get(username='vicente.sousa@x.com')
		self.assertEqual((u.first_name, u.last_name), ('Vicente', 'Sousa'))
		self._daftar('ana_maria99@x.com')                                                       # kolom tidak dikirim sama sekali
		u = User.objects.get(username='ana_maria99@x.com')
		self.assertEqual((u.first_name, u.last_name), ('Ana', 'Maria'))
		self._daftar('info@x.com', '')
		u = User.objects.get(username='info@x.com')
		self.assertEqual((u.first_name, u.last_name), ('', ''))                                 # bukan nama orang: dikosongkan

	def test_daftar_dengan_hp_tanpa_naran_tidak_ada_nama(self):
		self._daftar('77123456', '')
		u = User.objects.get(username='+67077123456')
		self.assertEqual((u.first_name, u.last_name), ('', ''))
		self._daftar('77123457', 'Joaquina Lopes')                                              # HP + naran diisi: tersimpan
		u = User.objects.get(username='+67077123457')
		self.assertEqual((u.first_name, u.last_name), ('Joaquina', 'Lopes'))

	def test_naran_tidak_valid_menggagalkan_daftar(self):
		for jelek in ('<script>', 'Ana123', 'A'):
			r = self._daftar(f'x{len(jelek)}@x.com', jelek)
			self.assertEqual(r.status_code, 200, jelek)
			self.assertContains(r, 'not valid')
		self.assertFalse(User.objects.filter(username__startswith='x').exists())

	def test_form_daftar_menampilkan_kolom_naran(self):
		r = self.client.get('/users/register/')
		self.assertContains(r, 'name="naran"')
		self.assertContains(r, 'Your name is optional')

	def test_akun_bisa_melihat_dan_mengubah_naran_termasuk_tamu(self):
		u = user_grup('akun1', 'pelajar')
		self.client.force_login(u)
		self.assertContains(self.client.get('/users/account/'), 'name="naran"')
		self.client.post('/users/account/', {'naran': 'vicente  sousa'})
		u.refresh_from_db()
		self.assertEqual((u.first_name, u.last_name), ('Vicente', 'Sousa'))
		self.assertContains(self.client.get('/users/account/'), 'value="Vicente Sousa"')
		self.client.post('/users/account/', {'naran': '<b>x'})                                  # tidak valid: tidak berubah
		u.refresh_from_db()
		self.assertEqual(u.first_name, 'Vicente')
		self.client.post('/users/account/', {'naran': ''})                                      # kosong: nama dihapus
		u.refresh_from_db()
		self.assertEqual((u.first_name, u.last_name), ('', ''))
		self.client.logout()
		self.client.post('/tamu/')                                                              # akun tamu juga boleh mengisi nama
		self.client.post('/users/peran/', {'peran': 'anak'})
		self.client.post('/users/account/', {'naran': 'Tito'})
		tamu = User.objects.get(username__startswith='tamu-')
		self.assertEqual(tamu.first_name, 'Tito')

	def test_naran_dipakai_sapaan_dan_di_escape(self):
		u = user_grup('akun2', 'pelajar')
		self.client.force_login(u)
		self.client.post('/users/account/', {'naran': 'maria da costa'})
		self.assertIn('data-nama="Maria"', self.client.get('/video-call/').content.decode())   # first_name -> sapaan
		self.client.post('/users/account/', {'naran': 'Ana'})
		self.assertContains(self.client.get('/users/account/'), 'value="Ana"')
		self.assertEqual(self.client.get('/users/account/').status_code, 200)

	def test_hanya_milik_sendiri(self):
		a, b = user_grup('ua', 'pelajar'), user_grup('ub', 'pelajar')
		self.client.force_login(a)
		self.client.post('/users/account/', {'naran': 'Ana', 'user': b.pk, 'first_name': 'Curang'})
		b.refresh_from_db(); a.refresh_from_db()
		self.assertEqual((a.first_name, b.first_name), ('Ana', ''))
