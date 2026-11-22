from django.conf import settings
"""Tes halaman utama, login, tamu, menu per group, dan PWA."""
import json

import re
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings

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

	@override_settings(HOME_LANGSUNG_BICARA=False)      # uji beranda berisi kartu menu (bila fitur 'langsung bicara' dimatikan)
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

	@override_settings(HOME_LANGSUNG_BICARA=False)      # uji beranda berisi kartu menu (bila fitur 'langsung bicara' dimatikan)
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
		self.client.force_login(user_grup('k-kon', 'kontributor'))
		html = self.client.get('/').content.decode()
		self.assertIn('href="/crowdsource/"', html)                      # kontributor merekam
		self.assertIn('href="/crowdsource/kontribusiku/"', html)
		self.client.force_login(user_grup('k-adm', 'admin'))
		html = self.client.get('/').content.decode()
		self.assertIn('href="/crowdsource/tinjau/"', html)               # admin meninjau, tidak merekam
		self.assertNotIn('href="/crowdsource/"', html)

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

	@override_settings(HOME_LANGSUNG_BICARA=False)      # uji beranda berisi kartu menu (bila fitur 'langsung bicara' dimatikan)
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


class BerandaLangsungBicara(TestCase):
	"""Pilihan 'HOME_LANGSUNG_BICARA' (bawaan MATI): pelajar/tamu dialihkan langsung ke /video-call/."""

	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)

	def test_bawaan_mati_siswa_tetap_punya_halaman_siswa(self):
		self.assertFalse(settings.HOME_LANGSUNG_BICARA)
		self.client.force_login(user_grup('p', 'pelajar'))
		self.assertEqual(self.client.get('/').status_code, 200)

	@override_settings(HOME_LANGSUNG_BICARA=True)
	def test_bila_dinyalakan_pelajar_dialihkan_dan_kontributor_admin_tidak(self):
		self.client.force_login(user_grup('p2', 'pelajar'))
		self.assertRedirects(self.client.get('/'), '/video-call/', fetch_redirect_response=False)
		for grup in ('kontributor', 'admin'):
			self.client.force_login(user_grup(f'u-{grup}', grup))
			self.assertEqual(self.client.get('/').status_code, 200, grup)


class LayarVideoCall(TestCase):
	"""Layar Video Call: tanpa pilihan apa pun; hanya status, subtitle, dan 3 tombol."""

	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)

	def setUp(self):
		self.client.force_login(user_grup('p', 'pelajar'))
		self.html = self.client.get('/video-call/?mode=pintar&bahasa=tetun&topik=bebas').content.decode()

	def test_semua_pilihan_dan_input_ketik_dihapus(self):
		for terlarang in ('id="pil-bahasa"', 'id="pil-topik"', 'data-menit', 'vc-menit', 'id="mulai"', 'MULAI PANGGILAN', 'id="input"', 'id="form"',
		                  'data-mode=', 'type="text"', 'MODE DEMO', 'id="lapis-awal"', 'Telefone fali', 'maskot', 'lafaek.svg', 'aksesori'):
			self.assertNotIn(terlarang, self.html, terlarang)

	def test_hanya_tiga_tombol_bawah(self):
		bawah = self.html[self.html.index('class="vc-kontrol"'):self.html.index('<script>')]
		self.assertEqual(sorted(re.findall(r'id="(\w+)"', bawah)), ['mik', 'tutup', 'ulangi'])
		self.assertEqual(bawah.count('<button'), 3)

	def test_unsur_wajib(self):
		for kunci in ('id="menu-buka"', 'id="waktu"', 'id="poin"', 'id="lafex-img"', 'id="status"', 'id="baris-siswa"', 'id="baris-lafex"', 'id="koreksi"',
		              "Hakarak hapara?", 'id="ya"', 'id="belum"', 'id="coba-lagi"', 'Tekan Izinkan Mikrofon di atas', "BOMDIA PRESIJA, MAUN LAFEX PREMAN BONITU AJUDA! {NAMA}! Oinsa? Mai ko'alia!",
		              "LAFEX Lagi Ngomong...", "LAFEX Lagi Dengerin... Ko'alia took!", "LAFEX Lagi Mikir...", "LAFEX Siap",
		              "Hau la rona ho diak, bele ko'alia fali?", 'data-img="/static/img/lafex/"', 'data-chat="/api/lafex-chat/"'):
			self.assertIn(kunci, self.html, kunci)

	def test_gambar_hanya_dua_belas_png_milik_pengguna(self):
		nama = ('preman', 'pintar', 'pro')
		for n in nama:
			for pose in ('diam', 'ngomong', 'jempol', 'mikir'):
				self.assertIn(f'"{n}_{pose}.png"', self.html)
		self.assertNotIn('http://', self.html.split('<script>')[1])
		self.assertNotIn('https://', self.html.split('<script>')[1])                # tidak ada gambar/sumber dari internet

	def test_pengenalan_suara_sesuai_aturan(self):
		js = self.html.split('<script>')[1]
		for kunci in ('r.continuous = false', 'r.interimResults = true', 'JEDA_MS = 2000', 'u.pitch = 1.0', 'hurufAngka(teks) < 3'):
			self.assertIn(kunci, js, kunci)

	def test_demo_hanya_pojok_kecil(self):
		from django.test import override_settings as os_
		self.assertIn('class="vc-demo">demo<', self.html)                               # backend demo: lencana kecil, bukan kalimat di tengah layar
		with os_(AI={**settings.AI, 'BACKEND': 'local'}):
			self.assertNotIn('class="vc-demo"', self.client.get('/video-call/').content.decode())


class BatasPerIP(TestCase):
	"""Batas per alamat IP: menahan akun massal, dan BENAR di belakang proxy (bukan satu hitungan untuk semua pengguna)."""

	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)

	def setUp(self):
		cache.clear()

	def _tamu(self, **kw):
		self.client.logout()
		return self.client.post('/tamu/', **kw)

	def test_alamat_klien_tanpa_proxy_mengabaikan_header_palsu(self):
		from django.test import RequestFactory
		from config.utils import alamat_klien
		r = RequestFactory().get('/', REMOTE_ADDR='203.0.113.7', HTTP_X_FORWARDED_FOR='9.9.9.9')
		self.assertEqual(alamat_klien(r), '203.0.113.7')                           # klien tidak bisa memalsukan IP lewat header

	@override_settings(BEHIND_PROXY=True)
	def test_alamat_klien_di_belakang_proxy_memakai_entri_terakhir(self):
		from django.test import RequestFactory
		from config.utils import alamat_klien
		r = RequestFactory().get('/', REMOTE_ADDR='10.0.0.1', HTTP_X_FORWARDED_FOR='6.6.6.6, 198.51.100.4')
		self.assertEqual(alamat_klien(r), '198.51.100.4')                           # entri awal (palsu) diabaikan
		self.assertEqual(alamat_klien(RequestFactory().get('/', REMOTE_ADDR='10.0.0.1')), '10.0.0.1')

	@override_settings(BATAS_IP={'TAMU_JAM': 3, 'DAFTAR_JAM': 30, 'TTS_MENIT': 120})
	def test_akun_tamu_dibatasi_per_ip(self):
		for _ in range(3):
			self.assertEqual(self._tamu(REMOTE_ADDR='203.0.113.9').status_code, 302)
		self.assertEqual(User.objects.filter(username__startswith='tamu-').count(), 3)
		self._tamu(REMOTE_ADDR='203.0.113.9')                                      # ke-4 dari IP yang sama
		self.assertEqual(User.objects.filter(username__startswith='tamu-').count(), 3)
		self._tamu(REMOTE_ADDR='203.0.113.10')                                     # IP lain tidak terpengaruh
		self.assertEqual(User.objects.filter(username__startswith='tamu-').count(), 4)

	@override_settings(BEHIND_PROXY=True, BATAS_IP={'TAMU_JAM': 2, 'DAFTAR_JAM': 30, 'TTS_MENIT': 120})
	def test_di_belakang_proxy_tiap_klien_dihitung_sendiri(self):
		for klien in ('198.51.100.1', '198.51.100.2', '198.51.100.3'):             # proxy sama (10.0.0.1), klien beda
			self._tamu(REMOTE_ADDR='10.0.0.1', HTTP_X_FORWARDED_FOR=klien)
		self.assertEqual(User.objects.filter(username__startswith='tamu-').count(), 3)      # dulu: hitungan bersama, pengguna ke-3 ditolak
		for _ in range(3):                                                         # satu klien yang sama melampaui batas, walau memalsukan entri awal
			self._tamu(REMOTE_ADDR='10.0.0.1', HTTP_X_FORWARDED_FOR=f'{_}.{_}.{_}.{_}, 198.51.100.50')
		self.assertEqual(User.objects.filter(username__startswith='tamu-').count(), 5)

	@override_settings(BATAS_IP={'TAMU_JAM': 60, 'DAFTAR_JAM': 2, 'TTS_MENIT': 120})
	def test_pendaftaran_dibatasi_per_ip(self):
		def daftar(n):
			self.client.logout()
			return self.client.post('/users/register/', {'kontak': f'orang{n}@contoh.com', 'password1': 'rahasia123', 'password2': 'rahasia123'}, REMOTE_ADDR='203.0.113.20')
		self.assertEqual([daftar(i).status_code for i in range(3)], [302, 302, 302])
		self.assertEqual(User.objects.filter(username__startswith='orang').count(), 2)     # yang ke-3 ditolak
		self.assertContains(self.client.get('/users/register/', follow=True), 'Too many sign-ups')


class SapaanNama(TestCase):
	"""Sapaan awal Video Call memakai NAMA user yang login (dari server), dengan teks PERSIS per mode."""

	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)

	def _halaman(self, user, url='/video-call/?mode=pintar'):
		self.client.force_login(user)
		return self.client.get(url).content.decode()

	def test_nama_tampil_dari_first_name_email_dan_bawaan_kosong(self):
		from config.user_utils import nama_tampil
		u = lambda **kw: User(username=kw.pop('username', 'x'), **kw)
		self.assertEqual(nama_tampil(u(first_name='vicente sousa')), 'Vicente')                  # first_name menang, hanya kata pertama
		self.assertEqual(nama_tampil(u(first_name='  ', email='vicente.sousa@gmail.com')), 'Vicente')
		self.assertEqual(nama_tampil(u(email='ana_maria99@x.com')), 'Ana')
		self.assertEqual(nama_tampil(u(email='joao123@x.com')), 'Joao')
		for tanpa_nama in ('info@x.com', 'admin@x.com', '12345@x.com', 'a@x.com', '', 'bukan-email'):
			self.assertEqual(nama_tampil(u(email=tanpa_nama)), '', tanpa_nama)                    # peran/angka/terlalu pendek: bukan nama
		self.assertEqual(nama_tampil(u(first_name='x' * 80)), 'X' + 'x' * 29)                     # dibatasi 30 huruf
		from django.contrib.auth.models import AnonymousUser
		self.assertEqual(nama_tampil(AnonymousUser()), '')

	def test_halaman_membawa_nama_yang_login_bukan_nama_contoh(self):
		self.assertIn('data-nama=""', self._halaman(user_grup('polos', 'pelajar')))              # tanpa nama/email: kosong (halaman memakai localStorage lalu "Maun / Mana")
		u = user_grup('vic', 'pelajar'); u.first_name = 'Vicente'; u.save()
		self.assertIn('data-nama="Vicente"', self._halaman(u))
		u2 = user_grup('mar', 'pelajar'); u2.email = 'maria.da@x.com'; u2.save()
		self.assertIn('data-nama="Maria"', self._halaman(u2))
		u3 = user_grup('peran', 'pelajar'); u3.email = 'info@x.com'; u3.save()
		self.assertIn('data-nama=""', self._halaman(u3))                                         # alamat layanan bukan nama orang
		self.client.logout()
		self.client.post('/tamu/')                                                               # akun tamu: tanpa nama
		self.client.post('/users/peran/', {'peran': 'anak'})
		self.assertIn('data-nama=""', self.client.get('/video-call/').content.decode())

	def test_nama_di_halaman_di_escape(self):
		u = user_grup('xss', 'pelajar'); u.first_name = '"><script>alert(1)</script>'; u.save()
		html = self._halaman(u)
		self.assertNotIn('<script>alert(1)', html.split('<script>')[0])
		self.assertIn('data-nama="&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"', html)

	def test_teks_sapaan_persis_per_mode_dan_aturan_teknis(self):
		js = self._halaman(user_grup('s1', 'pelajar')).split('<script>')[1]
		for kalimat in ('preman:       "BOMDIA PRESIJA, MAUN LAFEX PREMAN BONITU AJUDA! {NAMA}! Oinsa? Mai ko\'alia!"',
		                'pintar:       "BOMDIA PRESIJA, MAUN LAFEX AJUDA! {NAMA}! Mai aprende hamutuk!"',
		                'professional: "BOMDIA, MAUN LAFEX PREMAN BONITU AJUDA Sr./a {NAMA}! Diak ka lae? Mai ko\'alia ho profesional."'.replace("\\'", "'")):
			self.assertIn(kalimat.replace("\\'", "'"), js, kalimat)
		for kunci in ('NAMA_BAWAAN = "Maun / Mana"', 'JEDA_SAPA_MS = 1000', 'var namaUser = ambilNama()', 'sudahMenyapa', '"user_nama", "nama", "username"',
		              'ucapkan(teks, "tetun", 1.0, ucap)', 'u.pitch = 1.0', '"Diak tebes, " + namaUser', 'setTimeout(function () { sapa(false); }, JEDA_SAPA_MS)'):
			self.assertIn(kunci, js, kunci)
		self.assertNotIn('Vicente', js)                                                              # nama contoh tidak ada di kode
		badan = [b for b in js.splitlines() if 'JSON.stringify({ pesan' in b]
		self.assertEqual(len(badan), 1)
		self.assertNotIn('nama', badan[0].lower())                                                   # nama TIDAK dikirim ke backend/AI
