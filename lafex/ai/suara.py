"""
Sambungan ke server suara milik Anda sendiri (gratis, open-source), tanpa paket tambahan:
  - STT  = Whisper (faster-whisper-server / whisper.cpp server / LocalAI) lewat API kompatibel OpenAI: POST {STT_URL}/audio/transcriptions
  - TTS  = XTTS (mis. xtts-api-server)                                                              : POST {TTS_URL} {text, speaker_wav, language}
Keduanya MATI sampai URL diisi di .env. Whisper dan XTTS bawaan TIDAK mengenal Tetun; hasil baik baru bisa setelah
model di-fine-tune dengan data dari crowdsource (lihat docs/MELATIH_SUARA.md).
"""
import json
import urllib.error
import urllib.request
import uuid

from django.conf import settings


class SuaraGagal(Exception):
	"""Server suara tidak bisa dipakai. Pesan aman untuk ditampilkan."""


def stt_siap():
	return bool(settings.SUARA['STT_URL'])


def tts_siap():
	return bool(settings.SUARA['TTS_URL'])


def _multipart(bidang, nama_berkas, isi, tipe):
	batas = uuid.uuid4().hex
	bagian = []
	for k, v in bidang.items():
		bagian.append(f'--{batas}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
	bagian.append(f'--{batas}\r\nContent-Disposition: form-data; name="file"; filename="{nama_berkas}"\r\nContent-Type: {tipe}\r\n\r\n'.encode())
	bagian.append(isi)
	bagian.append(f'\r\n--{batas}--\r\n'.encode())
	return b''.join(bagian), f'multipart/form-data; boundary={batas}'


def transkripsi(isi_audio, nama='rekaman.webm', tipe='audio/webm', bahasa=''):
	"""Suara -> teks lewat Whisper. Return str (bisa kosong). Raise SuaraGagal."""
	cfg = settings.SUARA
	if not stt_siap():
		raise SuaraGagal('Whisper belum dikonfigurasi.')
	bidang = {'model': cfg['STT_MODEL'], 'response_format': 'json', 'temperature': '0'}
	if bahasa or cfg['STT_BAHASA']:
		bidang['language'] = bahasa or cfg['STT_BAHASA']
	badan, ctype = _multipart(bidang, nama, isi_audio, tipe)
	header = {'Content-Type': ctype}
	if cfg['STT_KUNCI']:
		header['Authorization'] = 'Bearer ' + cfg['STT_KUNCI']
	req = urllib.request.Request(cfg['STT_URL'].rstrip('/') + '/audio/transcriptions', data=badan, headers=header)
	try:
		with urllib.request.urlopen(req, timeout=cfg['STT_TIMEOUT']) as r:
			return str(json.loads(r.read().decode('utf-8')).get('text', '')).strip()
	except urllib.error.HTTPError:
		raise SuaraGagal('Whisper sedang bermasalah.')
	except (urllib.error.URLError, TimeoutError, OSError):
		raise SuaraGagal('Tidak bisa terhubung ke Whisper.')
	except (ValueError, AttributeError):
		raise SuaraGagal('Whisper sedang bermasalah.')


def sintesis(teks):
	"""Teks -> suara lewat XTTS. Return bytes audio (wav). Raise SuaraGagal."""
	cfg = settings.SUARA
	if not tts_siap():
		raise SuaraGagal('XTTS belum dikonfigurasi.')
	badan = json.dumps({'text': teks, 'speaker_wav': cfg['TTS_SUARA'], 'language': cfg['TTS_BAHASA']}).encode()
	header = {'Content-Type': 'application/json'}
	if cfg['TTS_KUNCI']:
		header['Authorization'] = 'Bearer ' + cfg['TTS_KUNCI']
	req = urllib.request.Request(cfg['TTS_URL'], data=badan, headers=header)
	try:
		with urllib.request.urlopen(req, timeout=cfg['TTS_TIMEOUT']) as r:
			audio = r.read(8 * 1024 * 1024 + 1)
	except urllib.error.HTTPError:
		raise SuaraGagal('XTTS sedang bermasalah.')
	except (urllib.error.URLError, TimeoutError, OSError):
		raise SuaraGagal('Tidak bisa terhubung ke XTTS.')
	if not audio or len(audio) > 8 * 1024 * 1024 or audio[:4] != b'RIFF':    # XTTS mengirim WAV
		raise SuaraGagal('XTTS tidak memberi suara.')
	return audio


def cek(url):
	"""Apakah server di url menjawab? (untuk halaman status admin). Return 'mati' | 'hidup' | 'belum diatur'."""
	if not url:
		return 'belum diatur'
	try:
		urllib.request.urlopen(urllib.request.Request(url, method='GET'), timeout=4).close()
		return 'hidup'
	except urllib.error.HTTPError:
		return 'hidup'                                     # server menjawab (mis. 405 untuk GET): berarti hidup
	except (urllib.error.URLError, TimeoutError, OSError):
		return 'mati'
