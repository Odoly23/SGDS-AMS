"""Tes config: teks 4 bahasa, kontak (email/HP), dekorator group."""
from django.contrib.auth.models import AnonymousUser, Group, User
from django.http import HttpResponse
from django.template import Context, Template
from django.test import RequestFactory, TestCase

from config import i18n
from config.decorators import allowed_users, unauthenticated_user
from config.user_utils import buat_user, nama_grup, normalisasi_kontak, pastikan_grup


class TeksEmpatBahasa(TestCase):
	def test_semua_teks_lengkap_di_4_bahasa(self):
		for kunci, d in i18n.TEKS.items():
			for kode in i18n.KODE:
				self.assertTrue(d.get(kode), f'{kunci} belum ada terjemahan {kode}')

	def test_tag_t_merender_keempat_bahasa(self):
		html = Template('{% load lian_tags %}{% t "record" %}').render(Context())
		for kata in ('Grava', 'Record', 'Gravar', 'Rekam'):     # contoh permintaan: Grava / Record / Rekam
			self.assertIn(kata, html)
		self.assertEqual(html.count('class="tx"'), 4)

	def test_tag_dengan_variabel_dan_xss(self):
		self.assertIn('20 kalimat', Template('{% load lian_tags %}{% t "kalimat_n" n=20 %}').render(Context()))
		from custom.models import Level
		html = Template('{% load lian_tags %}{% ml l "judul" %}').render(Context({'l': Level(nomor=1, judul_tet='<script>x</script>', judul_en='Market')}))
		self.assertNotIn('<script>', html)
		self.assertIn('Market', html)


class Kontak(TestCase):
	def test_email_dan_hp(self):
		self.assertEqual(normalisasi_kontak(' Ana@Contoh.COM '), ('email', 'ana@contoh.com'))
		for tulisan in ('7712 3456', '+670 7712 3456', '670-77123456', '0067077123456'):
			self.assertEqual(normalisasi_kontak(tulisan), ('telepon', '+67077123456'), tulisan)

	def test_tidak_valid(self):
		for salah in ('', 'abc', '1234', '3312345', 'a@b', '8812 3456'):
			with self.assertRaises(ValueError, msg=salah):
				normalisasi_kontak(salah)

	def test_buat_user_group_dan_perfil(self):
		u = buat_user(('telepon', '+67077123456'), 'rahasia123')
		self.assertEqual(nama_grup(u), 'pelajar')
		self.assertEqual(u.perfil.telepon, '+67077123456')
		self.assertEqual(len(u.perfil.kode_anonim), 12)
		self.assertEqual(Group.objects.count(), 3)


class Dekorator(TestCase):
	"""Dekorator dipakai APA ADANYA dari contoh SJDF."""
	def setUp(self):
		pastikan_grup()
		self.rf = RequestFactory()

	def _req(self, user):
		r = self.rf.get('/x')
		r.user = user
		return r

	def test_allowed_users_memeriksa_group_pertama(self):
		view = allowed_users(allowed_roles=['admin'])(lambda request: HttpResponse('ok'))
		boleh = User.objects.create_user('a')
		boleh.groups.add(Group.objects.get(name='admin'))
		lain = User.objects.create_user('b')
		lain.groups.add(Group.objects.get(name='pelajar'))
		tanpa = User.objects.create_user('c')
		self.assertEqual(view(self._req(boleh)).content, b'ok')
		self.assertNotEqual(view(self._req(lain)).content, b'ok')     # tampil halaman 404
		self.assertNotEqual(view(self._req(tanpa)).content, b'ok')

	def test_unauthenticated_user_mengalihkan_yang_sudah_masuk(self):
		view = unauthenticated_user(lambda request: HttpResponse('login'))
		self.assertEqual(view(self._req(AnonymousUser())).content, b'login')
		self.assertEqual(view(self._req(User.objects.create_user('d'))).status_code, 302)
