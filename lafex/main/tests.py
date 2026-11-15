"""Tes halaman utama, login, tamu, menu per group, dan PWA."""
import json

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from config.user_utils import buat_user, pastikan_grup
from users.models import Perfil


def user_grup(nama, grup, peran='dewasa'):
	u = User.objects.create_user(nama, password='rahasia123')
	u.groups.add(pastikan_grup()[grup])
	Perfil.objects.create(user=u, peran=peran)
	return u


class Dasar(TestCase):
	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)

	def setUp(self):
		cache.clear()


class HalamanDanMenu(Dasar):
	def test_belum_login_diarahkan_ke_login(self):
		for url in ('/', '/belajar/', '/ai/', '/crowdsource/', '/users/account/', '/report/'):
			r = self.client.get(url)
			self.assertEqual(r.status_code, 302, url)
			self.assertIn('/login/', r['Location'])

	def test_halaman_login_publik(self):
		r = self.client.get('/login/')
		self.assertEqual(r.status_code, 200)
		html = r.content.decode()
		self.assertIn('class="topbar"', html)          # pita tais di semua halaman
		for kode in ('tet', 'en', 'pt', 'id'):
			self.assertIn(f'data-set-lang="{kode}"', html)
		self.assertNotIn('id="sidebar"', html)         # belum login: tanpa menu

	def test_menu_per_group(self):
		cek = {
			'admin': dict(ada=['report-dash', 'u-list', 'crowdsource-home', 'belajar-list'], tak=[]),
			'kontributor': dict(ada=['crowdsource-home', 'belajar-list'], tak=['report/', 'users/list']),
			'pelajar': dict(ada=['belajar-list', 'ai/'], tak=['crowdsource/', 'report/', 'users/list']),
		}
		urls = {'report-dash': '/report/', 'u-list': '/users/list/', 'crowdsource-home': '/crowdsource/', 'belajar-list': '/belajar/'}
		for grup, c in cek.items():
			self.client.logout()
			self.client.force_login(user_grup(f'u-{grup}', grup))
			html = self.client.get('/').content.decode()
			nav = html[html.index('<header'):html.index('</header>')]      # hanya bagian menu (kartu beranda ada di luar)
			self.assertIn('id="sidebar"', nav)
			self.assertEqual(nav.count('class="nav-links"'), 1)
			for a in c['ada']:
				self.assertIn(urls.get(a, a), nav, f'{grup} harus punya {a}')
			for t in c['tak']:
				self.assertNotIn(t, nav, f'{grup} tidak boleh punya {t}')

	def test_beranda_menu_siswa_tanpa_latih_ai_dan_kontributor_empat_menu(self):
		self.client.force_login(user_grup('p', 'pelajar'))
		html = self.client.get('/').content.decode()
		for u in ("/ai/", "/belajar/", "/users/account/"):
			self.assertIn(f'href="{u}"', html)
		self.assertNotIn('href="/crowdsource/"', html)                   # siswa tidak perlu "latih AI"
		for n in range(1, 6):
			self.assertIn(f'href="/belajar/nivel/{n}/"', html)
		self.assertIn('class="fab-bicara"', html)
		self.assertIn('<html lang="tet"', html)
		for g in ('kontributor', 'admin'):
			self.client.force_login(user_grup(f'k-{g}', g))
			self.assertIn('href="/crowdsource/"', self.client.get('/').content.decode(), g)

	def test_pembatasan_group(self):
		self.client.force_login(user_grup('p', 'pelajar'))
		self.assertEqual(self.client.get('/belajar/').status_code, 200)
		for url in ('/report/', '/users/list/'):          # khusus admin: group lain melihat halaman 404 (pola dekorator SJDF)
			html = self.client.get(url).content.decode()
			self.assertIn('Página não encontrada', html, url)
			self.assertNotIn('class="stat"', html)
			self.assertNotIn('<table', html)
		html = self.client.get('/crowdsource/').content.decode()      # siswa: halaman 404 (pola SJDF), bukan fitur rekam
		self.assertIn('Página não encontrada', html)
		self.assertNotIn('id="cs"', html)
		self.client.force_login(user_grup('k', 'kontributor'))
		self.assertIn('id="cs"', self.client.get('/crowdsource/').content.decode())
		self.assertIn('Página não encontrada', self.client.get('/report/').content.decode())

	def test_pengguna_tanpa_group_tidak_bisa_masuk_halaman(self):
		u = User.objects.create_user('tanpa', password='x12345')
		self.client.force_login(u)
		html = self.client.get('/').content.decode()
		self.assertNotIn('class="nav-links"', html)
		self.assertNotIn('fab-bicara', html)

	def test_halaman_galat_dan_500_mandiri(self):
		self.assertEqual(self.client.get('/tidak-ada/').status_code, 404)
		from django.template.loader import render_to_string
		self.assertIn('LAFEX', render_to_string('home/500.html'))


class LoginTamu(Dasar):
	def test_login_email_dan_hp(self):
		buat_user(('email', 'ana@contoh.com'), 'rahasia123')
		buat_user(('telepon', '+67077123456'), 'rahasia123')
		for kontak in ('ANA@contoh.com', '7712 3456', '+670 7712 3456'):
			self.client.logout()
			r = self.client.post('/login/', {'kontak': kontak, 'password': 'rahasia123'})
			self.assertEqual(r.status_code, 302, kontak)
			self.assertIn('_auth_user_id', self.client.session)

	def test_login_salah_pesan_sama_dan_terkunci(self):
		buat_user(('email', 'ana@contoh.com'), 'rahasia123')
		r1 = self.client.post('/login/', {'kontak': 'ana@contoh.com', 'password': 'salah'})
		r2 = self.client.post('/login/', {'kontak': 'tidak@ada.com', 'password': 'salah'})
		self.assertContains(r1, 'salah')
		self.assertContains(r2, 'salah')       # tidak membocorkan akun mana yang ada
		for _ in range(7):
			r = self.client.post('/login/', {'kontak': 'ana@contoh.com', 'password': 'salah'})
		self.assertContains(r, 'Terlalu banyak')
		r = self.client.post('/login/', {'kontak': 'ana@contoh.com', 'password': 'rahasia123'})   # benar pun ditolak saat terkunci
		self.assertEqual(r.status_code, 200)

	def test_akun_nonaktif_tidak_bisa_masuk(self):
		u = buat_user(('email', 'ana@contoh.com'), 'rahasia123')
		u.is_active = False
		u.save()
		r = self.client.post('/login/', {'kontak': 'ana@contoh.com', 'password': 'rahasia123'})
		self.assertEqual(r.status_code, 200)
		self.assertNotIn('_auth_user_id', self.client.session)

	def test_tamu_lanjut_tanpa_daftar(self):
		self.assertEqual(self.client.get('/tamu/').status_code, 405)                  # hanya POST
		r = self.client.post('/tamu/')
		self.assertEqual(r.status_code, 302)
		u = User.objects.get(username__startswith='tamu-')
		self.assertTrue(u.perfil.is_tamu)
		self.assertFalse(u.has_usable_password())
		self.assertEqual(u.groups.first().name, 'pelajar')
		self.assertEqual(self.client.get('/belajar/').status_code, 200)

	def test_setelah_login_ditanya_kamu_siapa_sekali(self):
		buat_user(('email', 'ana@contoh.com'), 'rahasia123')
		self.client.post('/login/', {'kontak': 'ana@contoh.com', 'password': 'rahasia123'})
		self.assertEqual(self.client.get('/').status_code, 302)                      # -> /users/peran/
		self.assertEqual(self.client.get('/').url, '/users/peran/')
		self.client.post('/users/peran/', {'peran': 'ibu_pasar'})
		self.assertEqual(self.client.get('/').status_code, 200)
		self.assertEqual(User.objects.get(username='ana@contoh.com').perfil.peran, 'ibu_pasar')
		self.client.post('/users/peran/', {'peran': 'hacker'})                       # nilai ngawur ditolak
		self.assertEqual(User.objects.get(username='ana@contoh.com').perfil.peran, 'ibu_pasar')

	def test_logout_membersihkan_cache_halaman_dan_antrean_di_hp(self):
		self.client.force_login(user_grup('p', 'pelajar'))
		html = self.client.post('/logout/').content.decode()
		self.assertIn("indexOf('lafex-halaman')", html)
		self.assertIn('lafex_progres_antre', html)

	def test_logout_hanya_post(self):
		self.client.force_login(user_grup('p', 'pelajar'))
		self.assertEqual(self.client.get('/logout/').status_code, 405)
		r = self.client.post('/logout/')
		self.assertEqual(r.status_code, 200)
		self.assertNotIn('_auth_user_id', self.client.session)


class Pwa(Dasar):
	def test_manifest_dan_service_worker(self):
		r = self.client.get('/manifest.webmanifest')
		self.assertEqual(r['Content-Type'], 'application/manifest+json')
		m = json.loads(r.content)
		self.assertEqual((m['display'], m['name']), ('standalone', 'LAFEX - Lafaek Exploration'))
		self.assertTrue(any(i.get('purpose') == 'maskable' for i in m['icons']))
		sw = self.client.get('/sw.js')
		self.assertEqual(sw['Service-Worker-Allowed'], '/')
		self.assertIn('no-cache', sw['Cache-Control'])
		isi = sw.content.decode()
		self.assertIn('/offline/', isi)
		self.assertIn('(admin|users|report|login|logout|tamu)', isi)     # halaman pribadi tidak disimpan
		self.assertIn('lafex-halaman-', isi)                              # cache HTML terpisah dari cache berkas statis
		self.assertIn('lafex-statik-', isi)
		self.assertEqual(self.client.get('/offline/').status_code, 200)

	def test_semua_berkas_statis_di_cache_ada(self):
		import re
		from django.contrib.staticfiles import finders
		isi = self.client.get('/sw.js').content.decode()
		for path in re.findall(r'"/static/([^"]+)"', isi):
			self.assertTrue(finders.find(path), f'berkas statis tidak ada: {path}')


class BuatAdmin(Dasar):
	def test_buat_dan_naikkan_admin(self):
		from io import StringIO
		call_command('buat_admin', 'boss@contoh.com', '--password', 'rahasia123', stdout=StringIO())
		u = User.objects.get(username='boss@contoh.com')
		self.assertEqual((u.groups.first().name, u.is_superuser, u.is_staff), ('admin', True, True))
		self.client.force_login(u)
		self.assertContains(self.client.get('/report/'), 'class="stat"')          # lolos @allowed_users(['admin'])
		biasa = user_grup('biasa', 'pelajar')
		call_command('buat_admin', 'boss@contoh.com', stdout=StringIO())            # akun sudah ada: dinaikkan, tidak membuat baru
		self.assertEqual(User.objects.filter(username='boss@contoh.com').count(), 1)
		self.assertEqual(biasa.groups.count(), 1)

	def test_hp_dan_kata_sandi_pendek_ditolak(self):
		from django.core.management.base import CommandError
		with self.assertRaises(CommandError):
			call_command('buat_admin', 'bukan-kontak')
		with self.assertRaises(CommandError):
			call_command('buat_admin', '7712', '3456', '--password', '123')
