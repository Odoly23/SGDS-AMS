"""
Membuat akun ADMIN pertama (group `admin` + akses Admin Django), atau menaikkan akun yang sudah ada.
   python manage.py buat_admin admin@contoh.com
   python manage.py buat_admin 7712 3456 --password rahasia123   (kata sandi akan diminta bila tidak diberikan)
Kenapa bukan createsuperuser? Akun superuser TIDAK punya group, sehingga @allowed_users di aplikasi menampilkan 404.
"""
import getpass

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from config.user_utils import GRUP_ADMIN, buat_user, normalisasi_kontak, pastikan_grup


class Command(BaseCommand):
	help = "Buat / naikkan akun admin."

	def add_arguments(self, parser):
		parser.add_argument('kontak', nargs='+', help='email atau nomor HP')
		parser.add_argument('--password')

	def handle(self, *args, **o):
		try:
			kontak = normalisasi_kontak(' '.join(o['kontak']))
		except ValueError as e:
			raise CommandError(str(e))
		user = User.objects.filter(username=kontak[1]).first()
		if user is None:
			password = o['password'] or getpass.getpass('Kata sandi (min. 6 karakter): ')
			if len(password) < 6:
				raise CommandError('Kata sandi minimal 6 karakter.')
			user = buat_user(kontak, password, GRUP_ADMIN)
		else:
			user.groups.set([pastikan_grup()[GRUP_ADMIN]])      # satu group per user
		user.is_staff = user.is_superuser = user.is_active = True
		user.save()
		self.stdout.write(self.style.SUCCESS(f'{user.username} sekarang admin.'))
