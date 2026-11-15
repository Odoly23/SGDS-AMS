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
