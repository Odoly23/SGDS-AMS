"""Uji logika murni skrip (tanpa PyTorch):  python -m unittest training.test_finetune_whisper  (dari folder lafex/)"""
import json
import os
import tempfile
import unittest

from training import finetune_whisper as fw


class Murni(unittest.TestCase):
	def test_normalisasi_menjaga_apostrof_tetun(self):
		self.assertEqual(fw.normalisasi("  Bondia,  Ha'u Naran ANA! "), "bondia ha'u naran ana")
		self.assertEqual(fw.normalisasi("Ha’u"), "ha'u")

	def test_wer(self):
		self.assertEqual(fw.wer(['a b c d'], ['a b c d']), 0.0)
		self.assertEqual(fw.wer(['a b c d'], ['a x c']), 50.0)             # 1 ganti + 1 hapus dari 4 kata
		self.assertEqual(fw.wer(['bondia'], ['']), 100.0)
		self.assertEqual(fw.wer(['Bondia, Ha\'u!'], ["bondia ha'u"]), 0.0)    # tanda baca/huruf besar tidak dihitung
		self.assertEqual(fw.wer([''], ['apa saja']), 0.0)                  # acuan kosong diabaikan

	def _folder(self, baris, buat_wav=True):
		d = tempfile.mkdtemp()
		os.makedirs(os.path.join(d, 'wavs'))
		with open(os.path.join(d, 'train.jsonl'), 'w', encoding='utf-8') as f:
			for b in baris:
				f.write((json.dumps(b) if isinstance(b, dict) else b) + '\n')
		for b in baris:
			if buat_wav and isinstance(b, dict) and 'audio' in b:
				open(os.path.join(d, b['audio']), 'wb').write(b'x')
		return d

	def test_baca_manifest_melewati_baris_rusak_dan_berkas_hilang(self):
		d = self._folder([{'audio': 'wavs/r1.wav', 'text': 'Bondia'}, 'bukan json', {'audio': 'wavs/r2.wav', 'text': '  '}, {'text': 'tanpa audio'}, ''])
		os.path.exists(os.path.join(d, 'wavs/r2.wav'))
		data, lewat = fw.baca_manifest(d)
		self.assertEqual([x['text'] for x in data], ['Bondia'])
		self.assertEqual(lewat, 3)
		os.remove(os.path.join(d, 'wavs', 'r1.wav'))
		self.assertEqual(fw.baca_manifest(d)[0], [])
		with self.assertRaises(SystemExit):
			fw.baca_manifest(tempfile.mkdtemp())

	def test_bagi_menjaga_kalimat_sama_di_sisi_yang_sama(self):
		data = [{'audio': f'a{i}', 'text': f'Kalimat nomor {i % 40}.'} for i in range(400)]     # 40 kalimat x 10 penutur
		latih, dev = fw.bagi(data, 20)
		self.assertTrue(dev and latih)
		kalimat_latih = {fw.normalisasi(x['text']) for x in latih}
		self.assertFalse(kalimat_latih & {fw.normalisasi(x['text']) for x in dev})                 # tidak ada kebocoran
		self.assertEqual(len(latih) + len(dev), 400)
		self.assertEqual(fw.bagi(data, 20), (latih, dev))                                          # deterministik

	def test_bagi_data_sangat_sedikit_tetap_punya_dev(self):
		data = [{'audio': 'a', 'text': 'Satu'}, {'audio': 'b', 'text': 'Dua'}, {'audio': 'c', 'text': 'Dua'}]
		latih, dev = fw.bagi(data, 0)
		self.assertTrue(latih and dev)
		self.assertFalse({fw.normalisasi(x['text']) for x in latih} & {fw.normalisasi(x['text']) for x in dev})
		self.assertEqual(fw.bagi([{'audio': 'a', 'text': 'x'}], 0)[1], [])                          # 1 rekaman: tidak bisa dibagi


if __name__ == '__main__':
	unittest.main()
