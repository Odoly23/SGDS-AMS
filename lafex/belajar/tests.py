import tempfile

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from belajar.models import Kalimat, ProgresBelajar
from custom.models import Level
from main.tests import user_grup


class SeedLevel1(TestCase):
	def test_20_kalimat_4_materi_semua_draf_dan_lengkap_4_bahasa(self):
		call_command('seed_level1', verbosity=0)
		qs = Kalimat.objects.filter(materi__level__nomor=1)
		self.assertEqual((qs.count(), qs.values('materi').distinct().count()), (20, 4))
		self.assertEqual(set(qs.values_list('status', flat=True)), {'draft'})        # jujur: belum dicek penutur asli
		for k in qs:
			self.assertTrue(k.teks_tet and k.teks_en and k.teks_pt and k.teks_id, k.teks_tet)

	def test_idempoten_dan_tidak_menimpa_edit_admin(self):
		call_command('seed_level1', verbosity=0)
		k = Kalimat.objects.get(materi__level__nomor=1, materi__urutan=1, urutan=1)
		k.teks_tet, k.status = 'Bondia, mana!', 'terverifikasi'
		k.save()
		call_command('seed_level1', verbosity=0)
		k.refresh_from_db()
		self.assertEqual((k.teks_tet, k.status), ('Bondia, mana!', 'terverifikasi'))
		self.assertEqual(Kalimat.objects.count(), 20)


class Belajar(TestCase):
	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)
		call_command('seed_level1', verbosity=0)

	def setUp(self):
		cache.clear()
		self.u = user_grup('p', 'pelajar')
		self.client.force_login(self.u)

	def test_daftar_level_dengan_progress(self):
		for k in Kalimat.objects.filter(materi__level__nomor=1)[:5]:
			ProgresBelajar.objects.create(user=self.u, kalimat=k)
		r = self.client.get('/belajar/')
		self.assertEqual(r.status_code, 200)
		l1 = [l for l in r.context['levels'] if l.nomor == 1][0]
		self.assertEqual((l1.selesai, l1.total, l1.persen), (5, 20, 25))
		html = r.content.decode()
		self.assertIn('Ita aprende ona 5 husi 20', html)             # "Kamu sudah belajar 5 dari 20"
		self.assertIn('Kamu sudah belajar 5 dari 20', html)
		self.assertIn('Em breve', html)                              # level 2-5 belum ada kalimat

	def test_halaman_level_menampilkan_kalimat_4_bahasa_dan_tombol(self):
		html = self.client.get('/belajar/nivel/1/').content.decode()
		self.assertEqual(html.count('class="kalimat-kartu"'), 20)
		for teks in ('Bondia!', 'Good morning!', 'Bom dia!', 'Selamat pagi!'):
			self.assertIn(teks, html)
		self.assertEqual(html.count('class="btn-lian hitam btn-rekam"'), 20)                  # satu tombol rekam per kalimat
		self.assertIn('Grava ha', html)
		self.assertIn('disabled', html)                              # belum ada audio Tetun -> tombol Rona mati (jujur)
		self.assertIn('belum dicek penutur asli', html)              # catatan draf tampil
		self.assertIn('hanya di HP-mu', html)                        # rekaman latihan TIDAK diunggah

	def test_audio_tetun_mengaktifkan_tombol_dengar(self):
		with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
			k = Kalimat.objects.get(materi__level__nomor=1, materi__urutan=1, urutan=1)
			k.audio_tet.save('x.mp3', SimpleUploadedFile('x.mp3', b'ID3' + b'0' * 50), save=True)
			html = self.client.get('/belajar/nivel/1/').content.decode()
		self.assertIn('data-audio="/media/kalimat_audio/', html)

	def test_level_kosong_dan_tidak_ada(self):
		r = self.client.get('/belajar/nivel/2/')
		self.assertEqual(r.status_code, 200)
		self.assertIn('Coming soon', r.content.decode())
		self.assertEqual(self.client.get('/belajar/nivel/9/').status_code, 404)
		Level.objects.filter(nomor=3).update(aktif=False)
		self.assertEqual(self.client.get('/belajar/nivel/3/').status_code, 404)

	def test_progress_tandai_batal_dan_idempoten(self):
		k = Kalimat.objects.filter(materi__level__nomor=1).first()
		for _ in range(2):                                           # dua kali: tetap satu catatan
			r = self.client.post(f'/belajar/progresu/{k.pk}/')
		self.assertEqual(r.json(), {'selesai': 1, 'total': 20, 'persen': 5})
		self.assertEqual(ProgresBelajar.objects.count(), 1)
		r = self.client.post(f'/belajar/progresu/{k.pk}/', {'hapus': '1'})
		self.assertEqual(r.json()['selesai'], 0)
		self.assertEqual(ProgresBelajar.objects.count(), 0)

	def test_progress_per_user_terpisah(self):
		k = Kalimat.objects.filter(materi__level__nomor=1).first()
		self.client.post(f'/belajar/progresu/{k.pk}/')
		self.client.force_login(user_grup('lain', 'kontributor'))
		self.assertEqual(self.client.post(f'/belajar/progresu/{Kalimat.objects.filter(materi__level__nomor=1)[1].pk}/').json()['selesai'], 1)
		self.assertEqual(ProgresBelajar.objects.filter(user=self.u).count(), 1)
		html = self.client.get('/belajar/nivel/1/').content.decode()
		self.assertIn('data-done="1"', html)

	def test_progress_validasi(self):
		self.assertEqual(self.client.get('/belajar/progresu/1/').status_code, 405)
		self.assertEqual(self.client.post('/belajar/progresu/99999/').status_code, 404)
		k = Kalimat.objects.filter(materi__level__nomor=1).first()
		k.aktif = False
		k.save()
		self.assertEqual(self.client.post(f'/belajar/progresu/{k.pk}/').status_code, 404)
		self.client.logout()
		self.assertEqual(self.client.post('/belajar/progresu/1/').status_code, 302)       # belum login
		self.client.force_login(User.objects.create_user('tanpa', password='x12345'))      # tanpa group: ditolak dekorator
		k2 = Kalimat.objects.filter(materi__level__nomor=1, aktif=True).first()
		self.client.post(f'/belajar/progresu/{k2.pk}/')
		self.assertEqual(ProgresBelajar.objects.filter(user__username='tanpa').count(), 0)

	@override_settings(HOME_LANGSUNG_BICARA=False)      # uji beranda berisi kartu menu (bila fitur 'langsung bicara' dimatikan)
	def test_beranda_menaut_ke_halaman_level(self):
		self.u.perfil.peran = 'dewasa'
		self.u.perfil.save()
		self.assertIn('href="/belajar/nivel/1/"', self.client.get('/').content.decode())
