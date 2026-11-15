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
