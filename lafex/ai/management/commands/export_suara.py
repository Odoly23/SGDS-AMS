import csv
import json
import shutil
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from crowdsource.models import RekamanSuara


class Command(BaseCommand):
	help = ("Ekspor data latihan SUARA untuk fine-tune Whisper (suara->teks) dan XTTS (teks->suara): rekaman DISETUJUI + transkripsi "
	        "yang BUKAN draf Whisper. Tanpa nama/kode pengirim; nama berkas hanya nomor rekaman. Butuh ffmpeg.")

	def add_arguments(self, parser):
		parser.add_argument('--out', default='data_suara')
		parser.add_argument('--bahasa', default='', help="kode bahasa (mis. fataluku); kosong = semua. Latih SATU bahasa per model.")

	def handle(self, *a, **o):
		if not shutil.which('ffmpeg'):
			raise CommandError('ffmpeg tidak ditemukan. Pasang dulu (apt install ffmpeg).')
		qs = (RekamanSuara.objects.filter(status='disetujui').exclude(transkripsi='').exclude(sumber_transkripsi='otomatis')
		      .select_related('bahasa').order_by('pk'))
		if o['bahasa']:
			qs = qs.filter(bahasa__kode=o['bahasa'])
		out = Path(o['out'])
		jalur = {'whisper': 16000, 'xtts': 22050}
		for nama in jalur:
			(out / nama / 'wavs').mkdir(parents=True, exist_ok=True)
		n = gagal = 0
		detik = 0.0
		with open(out / 'whisper' / 'train.jsonl', 'w', encoding='utf-8') as jl, \
		     open(out / 'xtts' / 'metadata.csv', 'w', encoding='utf-8', newline='') as md:
			tulis = csv.writer(md, delimiter='|', lineterminator='\n')
			tulis.writerow(['audio_file', 'text', 'speaker_name'])
			for r in qs:
				teks = ' '.join(r.transkripsi.replace('|', ' ').split())
				if not teks or not r.audio:
					continue
				nama = f'r{r.pk}.wav'
				try:
					for jenis, hz in jalur.items():
						subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', r.audio.path, '-ac', '1', '-ar', str(hz),
						                str(out / jenis / 'wavs' / nama)], check=True, timeout=120)
				except (subprocess.SubprocessError, OSError, ValueError):
					gagal += 1
					continue
				jl.write(json.dumps({'audio': f'wavs/{nama}', 'text': teks, 'bahasa': r.bahasa.kode}, ensure_ascii=False) + '\n')
				tulis.writerow([f'wavs/{nama}', teks, 'lafex'])
				n += 1
				detik += r.durasi_detik or 0
		menit = round(detik / 60, 1)
		self.stdout.write(f'{n} rekaman ({menit} menit) ditulis ke {out}/  (gagal diubah: {gagal})')
		if menit < 60:
			self.stdout.write(self.style.WARNING('Kurang dari 1 jam: cukup untuk uji alur, TIDAK cukup untuk model yang bagus (butuh puluhan jam, banyak penutur).'))
