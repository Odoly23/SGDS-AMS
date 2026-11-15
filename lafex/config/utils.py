"""Fungsi bantu umum (gaya config/utils.py di SJDF: fungsi upload_to untuk tiap jenis berkas)."""
import os
import uuid


def _nama_acak(filename):
	"""Nama berkas diganti acak: nama asli (bisa memuat nama orang) tidak ikut tersimpan."""
	ext = os.path.splitext(filename)[1].lower()
	return f'{uuid.uuid4().hex}{ext}'


def kalimat_audio(instance, filename):
	"""audio contoh sebuah kalimat -> media/kalimat_audio/<id kalimat>/<acak>.ext"""
	return f'kalimat_audio/{instance.pk or "baru"}/{_nama_acak(filename)}'


def rekaman_suara(instance, filename):
	"""suara crowdsource -> media/rekaman_suara/<kode bahasa>/<acak>.ext (TIDAK memuat info pengirim)"""
	return f'rekaman_suara/{instance.bahasa.kode}/{_nama_acak(filename)}'
