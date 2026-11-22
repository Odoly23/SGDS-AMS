"""Fungsi bantu umum (gaya config/utils.py di SJDF: fungsi upload_to untuk tiap jenis berkas)."""
import os
import uuid

from django.conf import settings
from django.core.cache import cache


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


def alamat_klien(request):
	"""
	Alamat IP klien. Tanpa proxy: REMOTE_ADDR (header X-Forwarded-For dari klien TIDAK dipercaya, mudah dipalsukan).
	Di belakang proxy kita (DJANGO_BEHIND_PROXY=1): entri TERAKHIR X-Forwarded-For, yang ditambahkan proxy kita sendiri
	(REMOTE_ADDR di situ hanyalah alamat proxy, sama untuk semua pengguna).
	"""
	if settings.BEHIND_PROXY:
		bagian = [b.strip() for b in request.META.get('HTTP_X_FORWARDED_FOR', '').split(',') if b.strip()]
		if bagian:
			return bagian[-1][:64]
	return request.META.get('REMOTE_ADDR', '')[:64]


def lewat_batas_ip(request, nama, maks, detik):
	"""Hitung satu kejadian untuk IP klien; True bila sudah melewati `maks` dalam `detik` terakhir (jendela tetap)."""
	kunci = f'ip:{nama}:{alamat_klien(request)}'
	cache.add(kunci, 0, detik)
	return cache.incr(kunci) > maks
