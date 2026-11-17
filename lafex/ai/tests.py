import json
from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

import anthropic
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from ai import llm
from ai.models import Giliran
from custom.models import KarakterAI
from main.tests import user_grup


def ai_cfg(**kw):
	return override_settings(AI={**settings.AI, **kw})


class Dasar(TestCase):
	@classmethod
	def setUpTestData(cls):
		call_command('seed_awal', verbosity=0)

	def setUp(self):
		cache.clear()
		self.u = user_grup('pelajar1', 'pelajar', 'ibu_pasar')
		self.client.force_login(self.u)

	def bicara(self, teks='Bondia', karakter='sopan', **kw):
		return self.client.post('/ai/bicara/', json.dumps({'teks': teks, 'karakter': karakter, **kw}), content_type='application/json')


class Halaman(Dasar):
	def test_semua_group_bisa_buka_dan_belum_login_diarahkan(self):
		for g in ('admin', 'kontributor', 'pelajar'):
			self.client.force_login(user_grup(f'u-{g}', g))
			self.assertEqual(self.client.get('/ai/').status_code, 200, g)
		self.client.logout()
		self.assertEqual(self.client.get('/ai/').status_code, 302)

	def test_tiga_karakter_lafaek_dan_catatan_jujur(self):
		r = self.client.get('/ai/')
		html = r.content.decode()
		self.assertEqual(len(r.context['karakter_list']), 3)
		for nama in ('AI Bandidu', 'AI Respeitozu', 'AI Matenek'):      # nama Tetun
			self.assertIn(nama, html)
		self.assertIn('lafaek-buka.svg', html)                       # lafaek berbicara (mulut terbuka)
		self.assertIn('id="lafaek"', html)                           # lafaek = tombol bicara
		self.assertIn('Ulangi lian AI', html)                        # tombol "Ulangi Suara AI"
		self.assertIn('suara Portugis', html)                        # jujur: suara Tetun hanya perkiraan
		self.assertIn('layanan pengenalan suara', html)              # jujur: browser bisa mengirim suara ke vendor
		self.assertNotIn('class="fab-bicara"', html)                 # tombol buaya kecil disembunyikan di halaman ini
		self.assertEqual(r.context['sisa'], 40)
		self.assertTrue(r.context['demo'])
		self.assertIn('MODE DEMO', html)

	def test_karakter_nonaktif_tidak_tampil(self):
		KarakterAI.objects.filter(kode='preman').update(aktif=False)
		self.assertNotIn('data-kode="preman"', self.client.get('/ai/').content.decode())


class Bicara(Dasar):
	def test_giliran_berhasil_dan_tersimpan_teks_saja(self):
		r = self.bicara('Bondia, ha\'u hakarak sosa modo')
		d = r.json()
		self.assertTrue(d['ok'])
		self.assertTrue(d['tet'] and d['en'])                        # Tetun + Inggris
		self.assertTrue(d['demo'])                                   # mode demo ditandai
		self.assertEqual(d['sisa'], 39)
		g = Giliran.objects.get()
		self.assertEqual((g.user, g.karakter.kode, g.bahasa_ucap, g.ucapan), (self.u, 'sopan', 'tet', "Bondia, ha'u hakarak sosa modo"))
		self.assertEqual({f.name for f in Giliran._meta.concrete_fields} & {'audio', 'suara', 'file'}, set())   # suara TIDAK disimpan

	def test_gaya_karakter(self):
		self.assertTrue(self.bicara(karakter='preman').json()['tet'].startswith('Woi!'))
		self.assertTrue(self.bicara(karakter='sopan').json()['tet'].startswith('Favór ida'))

	def test_gerak_gerik_khas_karakter_dan_selalu_dari_daftar_tertutup(self):
		for karakter, bawaan in (('preman', 'jempol'), ('sopan', 'bungkuk'), ('profesional', 'angguk')):
			g = self.bicara('xyz tidak dikenal', karakter=karakter).json()['gerak']
			self.assertIn(g, llm.GERAK)
		self.assertEqual(self.bicara('Bondia', karakter='preman').json()['gerak'], 'lambai')
		self.assertEqual(self.bicara('modo fresku', karakter='preman').json()['gerak'], 'jempol')
		self.assertEqual(self.bicara('modo fresku', karakter='sopan').json()['gerak'], 'bungkuk')   # karakter hormat tidak acung jempol
		self.assertEqual(Giliran.objects.filter(gerak='lambai').count(), 1)
		self.assertTrue(all(x['gerak'] in llm.GERAK for x in self.client.get('/ai/riwayat/', {'karakter': 'preman'}).json()['riwayat']))

	def test_validasi(self):
		self.assertEqual(self.bicara('   ').status_code, 400)
		self.assertEqual(self.bicara('x' * 501).status_code, 400)
		self.assertEqual(self.bicara(karakter='tidak-ada').status_code, 400)
		KarakterAI.objects.filter(kode='preman').update(aktif=False)
		self.assertEqual(self.bicara(karakter='preman').status_code, 400)
		self.assertEqual(self.client.post('/ai/bicara/', 'bukan json', content_type='application/json').status_code, 400)
		self.assertEqual(Giliran.objects.count(), 0)
		self.bicara(bahasa='klingon')                                # bahasa ucap ngawur -> tet
		self.assertEqual(Giliran.objects.get().bahasa_ucap, 'tet')

	def test_metode_dan_akses(self):
		self.assertEqual(self.client.get('/ai/bicara/').status_code, 405)
		self.client.logout()
		self.assertEqual(self.bicara().status_code, 302)
		self.client.force_login(User.objects.create_user('tanpa-grup', password='x12345'))   # tanpa group: ditolak dekorator
		self.bicara()
		self.assertEqual(Giliran.objects.count(), 0)

	def test_batas_harian_dan_tamu_lebih_sedikit(self):
		with ai_cfg(BATAS_HARI=3):
			self.assertEqual([self.bicara().status_code for _ in range(4)], [200, 200, 200, 429])
			r = self.bicara()
			self.assertEqual((r.json()['kode'], r.json()['sisa']), ('batas', 0))
		self.client.logout()
		self.client.post('/tamu/')                                   # akun tamu baru: batas khusus
		with ai_cfg(BATAS_HARI_TAMU=2, BATAS_HARI=40):
			self.assertEqual([self.bicara().status_code for _ in range(3)], [200, 200, 429])

	def test_batas_per_menit(self):
		with ai_cfg(BATAS_MENIT=2):
			self.assertEqual([self.bicara().status_code for _ in range(3)], [200, 200, 429])
			self.assertEqual(self.bicara().json()['kode'], 'laju')

	def test_kemarin_tidak_dihitung_batas_hari_ini(self):
		self.bicara()
		Giliran.objects.update(datetime=timezone.now() - timedelta(days=1, hours=1))
		with ai_cfg(BATAS_HARI=1):
			self.assertEqual(self.bicara().status_code, 200)

	def test_model_gagal_tidak_dicatat_dan_tidak_mengurangi_jatah(self):
		with mock.patch('ai.llm.jawab', side_effect=llm.AIGagal('x')):
			r = self.bicara()
		self.assertEqual((r.status_code, r.json()['kode']), (503, 'galat'))
		self.assertEqual(Giliran.objects.count(), 0)
		self.assertEqual(self.bicara().json()['sisa'], 39)

	def test_konteks_hanya_milik_user_dan_karakter_ini_dan_terbatas(self):
		lain = user_grup('lain', 'pelajar')
		sopan, preman = KarakterAI.objects.get(kode='sopan'), KarakterAI.objects.get(kode='preman')
		def buat(user, karakter, teks, umur_jam=0):
			g = Giliran.objects.create(user=user, karakter=karakter, ucapan=teks, jawab_tet='t', jawab_en='e')
			Giliran.objects.filter(pk=g.pk).update(datetime=timezone.now() - timedelta(hours=umur_jam, minutes=1))
		buat(lain, sopan, 'RAHASIA-LAIN')
		buat(self.u, preman, 'GAYA-LAIN')
		buat(self.u, sopan, 'SUDAH-LAMA', umur_jam=9)
		for i in range(8):
			buat(self.u, sopan, f'giliran-{i}')
		dilihat = {}
		def palsu(karakter, peran, riwayat, ucapan, bahasa):
			dilihat.update(riwayat=[g.ucapan for g in riwayat], peran=peran)
			return llm.Hasil(tet='ok', en='ok')
		with mock.patch('ai.llm.jawab', palsu):
			self.bicara()
		self.assertEqual(dilihat['riwayat'], [f'giliran-{i}' for i in range(2, 8)])      # 6 terakhir, urut lama -> baru
		self.assertEqual(dilihat['peran'], 'ibu_pasar')                                  # materi disesuaikan peran user

	def test_riwayat_dan_hapus_hanya_milik_sendiri(self):
		for t in ('satu', 'dua'):
			self.bicara(t)
		lain = user_grup('lain', 'pelajar')
		Giliran.objects.create(user=lain, karakter=KarakterAI.objects.get(kode='sopan'), ucapan='RAHASIA', jawab_tet='x')
		r = self.client.get('/ai/riwayat/', {'karakter': 'sopan'}).json()['riwayat']
		self.assertEqual([x['ucapan'] for x in r], ['satu', 'dua'])
		self.assertNotIn('RAHASIA', json.dumps(r))
		self.assertEqual(self.client.get('/ai/riwayat/', {'karakter': 'ngawur'}).json()['riwayat'], [])
		self.assertEqual(self.client.post('/ai/hapus/').json()['dihapus'], 2)
		self.assertEqual(Giliran.objects.filter(user=lain).count(), 1)


class LapisanModel(Dasar):
	def _cfg(self, **kw):
		return ai_cfg(BACKEND='anthropic', ANTHROPIC_API_KEY='sk-test', MODEL='claude-opus-5-5', EFFORT='low', MAX_TOKENS=1500, **kw)

	def _resp(self, teks, stop='end_turn', tin=900, tout=120):
		return SimpleNamespace(content=[SimpleNamespace(type='thinking'), SimpleNamespace(type='text', text=teks)] if teks else [], stop_reason=stop,
		                       usage=SimpleNamespace(input_tokens=tin, output_tokens=tout, cache_creation_input_tokens=0, cache_read_input_tokens=0))

	def _klien(self, resp=None, exc=None):
		panggilan = []
		def create(**kw):
			panggilan.append(kw)
			if exc:
				raise exc
			return resp
		llm._client = SimpleNamespace(messages=SimpleNamespace(create=create))
		self.addCleanup(setattr, llm, '_client', None)
		return panggilan

	def test_bentuk_permintaan_ke_model_dan_tidak_membocorkan_data_pribadi(self):
		panggilan = self._klien(self._resp('{"tet": "Bondia! Ita diak ka lae?", "en": "Good morning! How are you?", "koreksi": ""}'))
		self.u.email = 'rahasia@contoh.com'
		self.u.save()
		with self._cfg():
			self.bicara('Bondia')
			r = self.bicara("Ha'u diak", karakter='sopan').json()
		k = panggilan[1]
		self.assertEqual((k['model'], k['max_tokens'], k['output_config']), ('claude-opus-5-5', 1500, {'effort': 'low'}))
		self.assertEqual([m['role'] for m in k['messages']], ['user', 'assistant', 'user'])
		self.assertEqual(k['messages'][-1]['content'], "Ha'u diak")
		self.assertEqual(json.loads(k['messages'][1]['content'])['tet'], 'Bondia! Ita diak ka lae?')   # riwayat dikirim sebagai JSON yang sama
		self.assertEqual(set(json.loads(k['messages'][1]['content'])), {'tet', 'en', 'koreksi', 'gerak'})
		self.assertIn('"gerak"', k['system'])                                                            # model diminta memilih gerak-gerik
		self.assertIn(KarakterAI.objects.get(kode='sopan').prompt_sistem[:40], k['system'])             # gaya dari prompt yang diatur Admin
		self.assertIn('JSON', k['system'])
		self.assertIn('pasar', k['system'])                                                              # konteks peran ibu_pasar
		blob = json.dumps(k, ensure_ascii=False)
		for rahasia in ('rahasia@contoh.com', 'pelajar1', str(self.u.pk) + '@'):
			self.assertNotIn(rahasia, blob)                                                              # nama/email user TIDAK dikirim ke API
		self.assertEqual((r['tet'], r['en'], r['demo']), ('Bondia! Ita diak ka lae?', 'Good morning! How are you?', False))
		g = Giliran.objects.last()
		self.assertEqual((g.token_masuk, g.token_keluar, g.model), (900, 120, 'claude-opus-5-5'))

	def test_prompt_yang_diubah_admin_langsung_dipakai(self):
		panggilan = self._klien(self._resp('{"tet": "ok", "en": "ok", "koreksi": ""}'))
		KarakterAI.objects.filter(kode='preman').update(prompt_sistem='GAYA-BARU-DARI-ADMIN-XYZ')
		with self._cfg():
			self.bicara(karakter='preman')
		self.assertIn('GAYA-BARU-DARI-ADMIN-XYZ', panggilan[0]['system'])

	def test_urai_jawaban_model(self):
		for teks, gerak in [('{"tet": "A", "gerak": "Jempol"}', 'jempol'), ('{"tet": "A", "gerak": "joget-gila"}', ''),
		                    ('{"tet": "A", "gerak": null}', ''), ('{"tet": "A"}', ''), ('{"tet": "A", "gerak": "*menari*"}', '')]:
			self.assertEqual(llm._hasil_dari_teks(teks).gerak, gerak, teks)             # gerak di luar daftar dibuang
		for teks, tet, kor in [
			('{"tet": "A", "en": "B", "koreksi": "C", "gerak": "jempol"}', 'A', 'C'),
			('```json\n{"tet": "A", "en": "B", "koreksi": ""}\n```', 'A', ''),
			('Baik! {"tet": "A", "en": "B", "koreksi": null} semoga membantu', 'A', ''),
			('Bondia, ita diak?', 'Bondia, ita diak?', ''),                       # bukan JSON: seluruh teks = jawaban Tetun
			('{"en": "tanpa tet"}', '{"en": "tanpa tet"}', ''),
		]:
			h = llm._hasil_dari_teks(teks)
			self.assertEqual((h.tet, h.koreksi), (tet, kor), teks)

	def test_penolakan_model_dan_jawaban_kosong_dan_galat_api(self):
		with self._cfg():
			self._klien(self._resp('', stop='refusal'))
			r = self.bicara().json()
			self.assertTrue(r['ok'] and "la bele ajuda" in r['tet'])
			self._klien(self._resp(''))
			self.assertEqual(self.bicara().status_code, 503)
			for exc in (anthropic.APIConnectionError(request=SimpleNamespace()),
			            anthropic.RateLimitError('x', response=SimpleNamespace(status_code=429, headers={}, request=SimpleNamespace()), body=None),
			            anthropic.AuthenticationError('x', response=SimpleNamespace(status_code=401, headers={}, request=SimpleNamespace()), body=None)):
				self._klien(exc=exc)
				self.assertEqual(self.bicara().status_code, 503, type(exc).__name__)
		with ai_cfg(BACKEND='anthropic', ANTHROPIC_API_KEY=''):
			self.assertEqual(self.bicara().status_code, 503)


class KarakterBaru(Dasar):
	def test_nama_tetun_deskripsi_tetun_dan_prompt_diperkaya(self):
		nama = {k.kode: k.nama_tet for k in KarakterAI.objects.all()}
		self.assertEqual(nama, {'preman': 'AI Bandidu', 'sopan': 'AI Respeitozu', 'profesional': 'AI Matenek'})
		for k in KarakterAI.objects.all():
			self.assertNotIn('Gaya jalan', k.deskripsi_tet)                    # deskripsi Tetun tidak boleh berisi bahasa Indonesia
			self.assertIn('GAYA BICARA', k.prompt_sistem)
			self.assertIn('GERAK-GERIK', k.prompt_sistem)
		preman, sopan, pro = (KarakterAI.objects.get(kode=c).prompt_sistem for c in ('preman', 'sopan', 'profesional'))
		self.assertIn('BATAS KERAS', preman)                                   # "Bandidu" hanya persona lucu: batas keselamatan tetap
		self.assertIn('jangan menghina', preman)
		self.assertIn('"Ita boot"', sopan)
		self.assertIn('Bele mós dehan', sopan)                                 # koreksi lembut sebagai saran
		self.assertIn('Uluk', pro)

	def test_aksesori_dan_lafaek_berbicara_tersedia_untuk_tiap_karakter(self):
		from django.contrib.staticfiles import finders
		for kode in ('preman', 'sopan', 'profesional'):
			self.assertTrue(finders.find(f'main/images/aksesori-{kode}.svg'), kode)
		self.assertTrue(finders.find('main/images/lafaek-buka.svg'))
		html = self.client.get('/ai/').content.decode()
		for kode in ('preman', 'sopan', 'profesional'):
			self.assertIn(f'aksesori-{kode}.svg', html)

	def test_semua_animasi_gerak_ada_di_css(self):
		from django.contrib.staticfiles import finders
		css = open(finders.find('main/css/main.css'), encoding='utf-8').read()
		for g in llm.GERAK:
			self.assertIn(f'.gerak.gerak-{g}', css, g)
		for gaya in ('preman', 'sopan', 'profesional'):
			self.assertIn(f'[data-keadaan="bicara"][data-gaya="{gaya}"]', css)


class ModelLokal(Dasar):
	"""Backend 'local': server kompatibel OpenAI (Ollama/llama.cpp/vLLM). Dipalsukan, tidak ada jaringan sungguhan."""

	def _balasan(self, isi, status=200):
		import io
		import urllib.error
		if status != 200:
			return urllib.error.HTTPError('http://x', status, 'x', {}, io.BytesIO(b''))
		resp = mock.MagicMock()
		resp.__enter__.return_value.read.return_value = json.dumps(
			{'choices': [{'message': {'content': isi}}], 'usage': {'prompt_tokens': 12, 'completion_tokens': 7}}).encode()
		return resp

	def test_jawaban_json_dibaca(self):
		isi = '{"tet": "Bondia!", "en": "Good morning!", "koreksi": "", "gerak": "lambai"}'
		with ai_cfg(BACKEND='local'), mock.patch('urllib.request.urlopen', return_value=self._balasan(isi)) as m:
			h = llm.jawab(KarakterAI.objects.first(), '', [], 'bondia', 'tet')
		self.assertEqual((h.tet, h.gerak, h.token_masuk, h.token_keluar), ('Bondia!', 'lambai', 12, 7))
		self.assertEqual(m.call_args[0][0].full_url, settings.AI['LOCAL_URL'].rstrip('/') + '/chat/completions')

	def test_server_mati_atau_error_menjadi_AIGagal(self):
		import urllib.error
		with ai_cfg(BACKEND='local'):
			for efek in (urllib.error.URLError('mati'), self._balasan('', 500), self._balasan('', 429)):
				with mock.patch('urllib.request.urlopen', side_effect=efek):
					with self.assertRaises(llm.AIGagal):
						llm.jawab(KarakterAI.objects.first(), '', [], 'halo', 'tet')

	def test_tanpa_url_ditolak(self):
		with ai_cfg(BACKEND='local', LOCAL_URL=''):
			with self.assertRaises(llm.AIGagal):
				llm.jawab(KarakterAI.objects.first(), '', [], 'halo', 'tet')

	def test_export_finetune(self):
		import os
		import tempfile
		path = os.path.join(tempfile.mkdtemp(), 't.jsonl')
		call_command('seed_level1', verbosity=0)
		call_command('export_finetune', out=path, semua=True, stdout=mock.MagicMock())
		baris = [json.loads(b) for b in open(path, encoding='utf-8')]
		self.assertTrue(baris)
		self.assertEqual([m['role'] for m in baris[0]['messages']], ['system', 'user', 'assistant'])
		json.loads(baris[0]['messages'][2]['content'])               # jawaban berformat JSON aplikasi
