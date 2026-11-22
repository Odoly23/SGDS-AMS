"""Bantuan untuk akun & group. Setiap user hanya punya SATU group (sama seperti SJDF)."""
import re

from django.contrib.auth.models import Group, User

GRUP_ADMIN = 'admin'              # mengelola semuanya
GRUP_KONTRIBUTOR = 'kontributor'  # boleh ikut crowdsource suara (diberikan admin)
GRUP_PELAJAR = 'pelajar'          # akun biasa & tamu: belajar + bicara dengan AI
SEMUA_GRUP = [GRUP_ADMIN, GRUP_KONTRIBUTOR, GRUP_PELAJAR]


def pastikan_grup():
	"""Buat ketiga group bila belum ada (dipanggil seed_awal dan saat daftar)."""
	return {n: Group.objects.get_or_create(name=n)[0] for n in SEMUA_GRUP}


def nama_grup(user):
	"""Nama group pertama user, atau '' bila tidak punya (sama dengan yang dipakai allowed_users)."""
	if user.is_authenticated and user.groups.exists():
		return user.groups.all()[0].name
	return ''


def normalisasi_kontak(teks):
	"""
	Terima email ATAU nomor HP. Return (jenis, nilai) -> ('email','a@b.com') atau ('telepon','+67077123456').
	Nomor HP Timor-Leste: 8 digit diawali 7 (boleh ditulis dengan +670 / 670 / spasi). Raise ValueError bila salah.
	"""
	teks = (teks or '').strip()
	if '@' in teks:
		if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', teks) or len(teks) > 150:
			raise ValueError('Email tidak valid.')
		return 'email', teks.lower()
	digit = re.sub(r'\D', '', teks)
	if digit.startswith('00670'):
		digit = digit[5:]
	elif digit.startswith('670') and len(digit) == 11:
		digit = digit[3:]
	if re.fullmatch(r'7\d{7}', digit):
		return 'telepon', f'+670{digit}'
	raise ValueError('Nomor HP tidak valid. Contoh: 7712 3456')


def buat_user(kontak, password, grup=GRUP_PELAJAR):
	"""Buat User + Perfil + masukkan ke group. `kontak` sudah dinormalisasi lewat normalisasi_kontak."""
	from users.models import Perfil
	jenis, nilai = kontak
	user = User.objects.create_user(username=nilai, email=nilai if jenis == 'email' else '', password=password)
	user.groups.add(pastikan_grup()[grup])
	Perfil.objects.create(user=user, telepon=nilai if jenis == 'telepon' else None)
	return user


# Bagian depan email yang bukan nama orang (alamat peran/layanan)
_BUKAN_NAMA = {'info', 'admin', 'user', 'users', 'test', 'tes', 'mail', 'email', 'contact', 'kontak', 'support', 'noreply', 'no', 'hello', 'halo',
               'siswa', 'murid', 'guru', 'akun', 'tamu', 'demo', 'lafex'}


def nama_tampil(user):
	"""
	Nama untuk sapaan di layar Video Call (ditampilkan di layar pengguna itu sendiri; TIDAK dikirim ke model AI).
	Urutan: first_name -> bagian depan email yang berbentuk nama (mis. 'vicente.sousa@x.com' -> 'Vicente') -> '' (tamu, akun HP, atau email tanpa nama).
	Aplikasi ini belum punya kolom nama sendiri; first_name bisa diisi admin di admin Django.
	"""
	if not getattr(user, 'is_authenticated', False):
		return ''
	nama = (user.first_name or '').strip().split(' ')[0] if (user.first_name or '').strip() else ''
	if not nama:
		email = (user.email or '').strip()
		if '@' in email:
			depan = email.split('@')[0]
			for bagian in re.split(r'[._\-+0-9]+', depan):
				if len(bagian) >= 2 and bagian.isalpha() and bagian.lower() not in _BUKAN_NAMA:
					nama = bagian
					break
	return nama[:30].capitalize() if nama else ''
