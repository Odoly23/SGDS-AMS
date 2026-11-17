import json

from django.core.management.base import BaseCommand

from ai.llm import bangun_sistem
from belajar.models import Kalimat
from custom.models import KarakterAI


class Command(BaseCommand):
	help = "Ekspor data latihan (JSONL format chat) untuk fine-tune Gemma/Llama dkk dengan LoRA. Hanya kalimat terverifikasi, tanpa data pribadi."

	def add_arguments(self, parser):
		parser.add_argument('--out', default='train.jsonl')
		parser.add_argument('--semua', action='store_true', help="Ikutkan juga kalimat draf (TIDAK disarankan: teks draf belum dicek penutur asli)")

	def handle(self, *a, **o):
		qs = Kalimat.objects.filter(aktif=True)
		if not o['semua']:
			qs = qs.filter(status='terverifikasi')
		karakter = KarakterAI.objects.first()
		n = 0
		with open(o['out'], 'w', encoding='utf-8') as f:
			for k in qs:
				if not k.teks_tet:
					continue
				for kode, teks in (('en', k.teks_en), ('pt', k.teks_pt), ('id', k.teks_id)):
					if not teks:
						continue
					# Pengguna menyapa dalam bahasa lain -> AI menjawab Tetun + terjemahan Inggris (format yang sama dengan aplikasi)
					sistem = bangun_sistem(karakter, '', kode) if karakter else ''
					jawab = {'tet': k.teks_tet, 'en': k.teks_en or '', 'koreksi': '', 'gerak': 'senyum'}
					f.write(json.dumps({'messages': [{'role': 'system', 'content': sistem}, {'role': 'user', 'content': teks},
					        {'role': 'assistant', 'content': json.dumps(jawab, ensure_ascii=False)}]}, ensure_ascii=False) + '\n')
					n += 1
		self.stdout.write(f'{n} contoh ditulis ke {o["out"]}')
		if n < 500:
			self.stdout.write(self.style.WARNING('Masih sedikit (<500). Model kecil butuh ribuan contoh bagus; tambah dan verifikasi dulu kalimatnya.'))
