import tempfile
from datetime import timedelta

from django.utils import timezone

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from belajar.models import Kalimat
from crowdsource.models import RekamanSuara
from custom.models import Bahasa, KarakterAI, Level, Materi
from main.tests import user_grup


class Dashboard(TestCase):
	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)

	def test_hanya_admin(self):
		self.client.force_login(user_grup('k', 'kontributor'))
		self.assertNotContains(self.client.get('/report/'), 'class="stat"')
		self.client.force_login(user_grup('a', 'admin'))
		self.assertContains(self.client.get('/report/'), 'class="stat"')

	def test_hitungan_per_bahasa(self):
		kal = Kalimat.objects.create(materi=Materi.objects.create(level=Level.objects.get(nomor=1), judul_tet='m'), teks_tet='x')
		with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
			for kode, status in (('fataluku', 'menunggu'), ('fataluku', 'disetujui'), ('mambae', 'menunggu')):
				RekamanSuara.objects.create(kalimat=kal, bahasa=Bahasa.objects.get(kode=kode), gaya=KarakterAI.objects.get(kode='sopan'),
				                            audio=SimpleUploadedFile('a.webm', b'x'), status=status)
		self.client.force_login(user_grup('a', 'admin'))
		r = self.client.get('/report/')
		self.assertEqual((r.context['jumlah_suara'], r.context['menunggu'], r.context['disetujui']), (3, 2, 1))
		per = {b.kode: (b.total, b.persen) for b in r.context['per_bahasa']}
		self.assertEqual(per, {'fataluku': (2, 100), 'mambae': (1, 50)})


	def test_pemakaian_ai_hari_ini_untuk_memantau_biaya(self):
		from ai.models import Giliran
		u = user_grup('p', 'pelajar')
		k = KarakterAI.objects.get(kode='sopan')
		Giliran.objects.create(user=u, karakter=k, ucapan='a', jawab_tet='b', token_masuk=900, token_keluar=100)
		Giliran.objects.create(user=u, karakter=k, ucapan='a', jawab_tet='b', token_masuk=500, token_keluar=50)
		lama = Giliran.objects.create(user=u, karakter=k, ucapan='a', jawab_tet='b', token_masuk=9999, token_keluar=9999)
		Giliran.objects.filter(pk=lama.pk).update(datetime=timezone.now() - timedelta(days=2))
		self.client.force_login(user_grup('a', 'admin'))
		r = self.client.get('/report/')
		self.assertEqual((r.context['giliran_ai'], r.context['token_ai']), (2, 1550))
