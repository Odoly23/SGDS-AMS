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
# Kata penghubung dalam nama Timor/Portugis: ditulis huruf kecil bila bukan kata pertama ("Maria da Costa")
_PARTIKEL = {'da', 'de', 'do', 'dos', 'das', 'di', 'du'}
NARAN_MAKS = 60
_POLA_NARAN = re.compile(r"^[^\W\d_](?:[^\W\d_]|['\u2019.\- ])*$")        # huruf (termasuk beraksen), spasi, apostrof, titik, tanda hubung; tanpa angka/simbol


def naran_valid(teks):
	teks = ' '.join(str(teks or '').split())
	return 2 <= len(teks) <= NARAN_MAKS and bool(_POLA_NARAN.match(teks))


def rapikan_naran(teks):
	"""'vicente  SOUSA' -> 'Vicente Sousa'; 'maria da costa' -> 'Maria da Costa'. Kata yang sudah campur besar-kecil ('McDonald') dibiarkan."""
	kata = ' '.join(str(teks or '').split())[:NARAN_MAKS].split(' ')
	hasil = []
	for i, k in enumerate(kata):
		if i > 0 and k.lower() in _PARTIKEL:
			hasil.append(k.lower())
		elif k.islower() or k.isupper():
			hasil.append(k[:1].upper() + k[1:].lower())
		else:
			hasil.append(k)
	return ' '.join(hasil)


def pisah_naran(teks):
	"""Nama lengkap -> (first_name, last_name): kata pertama = first_name, sisanya = last_name ('Maria da Costa' -> 'Maria', 'da Costa')."""
	kata = rapikan_naran(teks).split(' ')
	kata = [k for k in kata if k]
	return (kata[0], ' '.join(kata[1:])) if kata else ('', '')


def naran_dari_email(email):
	"""
	Tebakan nama dari bagian depan email: 'vicente.sousa@x.com' -> 'Vicente Sousa'; 'ana_maria99@x.com' -> 'Ana Maria'.
	Alamat layanan ('info@', 'admin@'), angka saja, atau kata terlalu pendek -> ''. Hanya tebakan: pengguna bisa mengubahnya di halaman Akun.
	"""
	email = str(email or '').strip()
	if '@' not in email:
		return ''
	kata = [k for k in re.split(r'[._\-+0-9]+', email.split('@')[0]) if len(k) >= 2 and k.isalpha()]
	if not kata or kata[0].lower() in _BUKAN_NAMA:
		return ''
	return rapikan_naran(' '.join(kata[:4]))


def isi_naran(user, teks):
	"""Simpan nama lengkap sebagai first_name + last_name TERPISAH (teks kosong -> keduanya dikosongkan)."""
	user.first_name, user.last_name = pisah_naran(teks)
	user.save(update_fields=['first_name', 'last_name'])


def nama_tampil(user):
	"""
	Nama untuk sapaan di layar Video Call (ditampilkan di layar pengguna itu sendiri; TIDAK dikirim ke model AI).
	Urutan: first_name (dari kolom Naran) -> tebakan dari email (akun lama yang belum punya nama) -> '' (tamu / akun HP: halaman memakai "Maun / Mana").
	"""
	if not getattr(user, 'is_authenticated', False):
		return ''
	nama = (user.first_name or '').strip().split(' ')[0]
	if not nama:
		nama = naran_dari_email(user.email).split(' ')[0]
	return rapikan_naran(nama)[:30]
