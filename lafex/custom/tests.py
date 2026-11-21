import json
from pathlib import Path

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

LAMA = json.loads((Path(__file__).parent / 'migrations' / '0003_karakter_nama_tetun.py').read_text().split('LAMA = ')[1].split('\n\nBARU')[0])


class MigrasiKarakter(TransactionTestCase):
	"""Data lama diperbarui ke nama Tetun baru, tetapi suntingan Admin TIDAK ditimpa."""

	def _migrasi(self, target):
		ex = MigrationExecutor(connection)
		ex.migrate(target)
		return ex.loader.project_state(target).apps

	def test_bawaan_lama_diperbarui_dan_suntingan_admin_dipertahankan(self):
		apps = self._migrasi([('custom', '0002_alter_karakterai_kode')])
		K = apps.get_model('custom', 'KarakterAI')
		for kode in ('preman', 'sopan', 'profesional'):
			K.objects.create(kode=kode, nama_pt='IA Educada' if kode == 'sopan' else '', prompt_sistem=LAMA[kode]['prompt_sistem'],
			                 nama_tet=LAMA[kode]['nama_tet'], deskripsi_tet=LAMA[kode]['deskripsi_tet'])
		K.objects.filter(kode='profesional').update(nama_tet='AI Pro Kustom')                  # Admin sudah mengubah nama
		K.objects.filter(kode='sopan').update(prompt_sistem='PROMPT KUSTOM ADMIN')             # dan prompt
		apps = self._migrasi([('custom', '0003_karakter_nama_tetun')])
		K = apps.get_model('custom', 'KarakterAI')
		pre, sop, pro = (K.objects.get(kode=k) for k in ('preman', 'sopan', 'profesional'))
		self.assertEqual(pre.nama_tet, 'AI Bandidu')
		self.assertIn("laran-di'ak", pre.deskripsi_tet)                                          # deskripsi Tetun yang tadinya berbahasa Indonesia
		self.assertIn('GERAK-GERIK', pre.prompt_sistem)                                          # prompt bawaan diganti versi baru
		self.assertEqual(sop.nama_tet, 'AI Respeitozu')
		self.assertEqual(sop.prompt_sistem, 'PROMPT KUSTOM ADMIN')                               # suntingan Admin dipertahankan
		self.assertEqual(pro.nama_tet, 'AI Pro Kustom')                                          # dipertahankan
		self.assertIn('GERAK-GERIK', pro.prompt_sistem)                                          # yang tidak disunting tetap diperbarui
		self._migrasi(MigrationExecutor(connection).loader.graph.leaf_nodes())                   # kembali ke versi terbaru untuk tes lain
