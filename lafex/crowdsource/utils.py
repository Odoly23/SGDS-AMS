"""Bantuan crowdsource: mengenali jenis berkas suara dari ISI-nya (bukan dari nama/ekstensi yang bisa dipalsukan)."""


def jenis_audio(head):
	"""Dari 16 byte pertama berkas -> 'webm' | 'ogg' | 'wav' | 'm4a' | 'mp3', atau None bila bukan audio yang kita terima."""
	if head[:4] == b'\x1aE\xdf\xa3':
		return 'webm'
	if head[:4] == b'OggS':
		return 'ogg'
	if head[:4] == b'RIFF' and head[8:12] == b'WAVE':
		return 'wav'
	if head[4:8] == b'ftyp':
		return 'm4a'
	if head[:3] == b'ID3' or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
		return 'mp3'
	return None


# Tipe konten yang KITA tentukan sendiri dari hasil jenis_audio(); Content-Type kiriman klien tidak pernah dipercaya
# (kalau dipercaya, berkas "OggS<script>..." berlabel text/html akan dieksekusi sebagai halaman saat admin membukanya langsung).
TIPE_AUDIO = {'webm': 'audio/webm', 'ogg': 'audio/ogg', 'wav': 'audio/wav', 'm4a': 'audio/mp4', 'mp3': 'audio/mpeg'}


def tipe_dari_nama(nama):
	"""Nama berkas hasil unggahan selalu 'rekaman.<ext>' (ext dari isi). Tidak dikenal -> application/octet-stream."""
	ext = str(nama).rsplit('.', 1)[-1].lower() if '.' in str(nama) else ''
	return TIPE_AUDIO.get(ext, 'application/octet-stream')
