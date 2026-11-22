from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from config.user_utils import naran_valid, normalisasi_kontak, rapikan_naran
from users.models import Perfil


class DaftarForm(forms.Form):
	"""Daftar dengan email ATAU nomor HP + kata sandi."""
	naran = forms.CharField(max_length=80, required=False, label="Naran",
							widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'autocomplete': 'name', 'placeholder': 'Ex: Vicente Sousa'}))
	kontak = forms.CharField(max_length=150, label="Email / Nu. Telefone",
							 widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'autocomplete': 'username', 'inputmode': 'email'}))
	password1 = forms.CharField(label="Palavra-pase", widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg', 'autocomplete': 'new-password'}))
	password2 = forms.CharField(label="Hakerek fali palavra-pase", widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg', 'autocomplete': 'new-password'}))

	def clean_naran(self):
		naran = ' '.join(self.cleaned_data.get('naran', '').split())
		if naran and not naran_valid(naran):
			raise forms.ValidationError('err_name_invalid')           # huruf/spasi saja, 2-60 karakter
		return rapikan_naran(naran)

	def clean_kontak(self):
		try:
			jenis, nilai = normalisasi_kontak(self.cleaned_data['kontak'])
		except ValueError:
			raise forms.ValidationError('err_contact_invalid')       # kunci teks 4 bahasa (lihat config/i18n.py)
		if User.objects.filter(username=nilai).exists() or (jenis == 'telepon' and Perfil.objects.filter(telepon=nilai).exists()):
			raise forms.ValidationError('err_contact_taken')
		self.kontak_normal = (jenis, nilai)
		return self.cleaned_data['kontak']

	def clean(self):
		data = super().clean()
		p1, p2 = data.get('password1'), data.get('password2')
		if p1 and p2 and p1 != p2:
			self.add_error('password2', 'err_pw_mismatch')
		elif p1:
			try:
				validate_password(p1)
			except forms.ValidationError as e:
				kode = {x.code for x in e.error_list}
				self.add_error('password1', 'err_pw_short' if 'password_too_short' in kode else 'err_pw_common')
		return data


class PeranForm(forms.ModelForm):
	class Meta:
		model = Perfil
		fields = ['peran']


class NaranForm(forms.Form):
	"""Ubah nama di halaman Akun (juga untuk akun tamu). Kosong = hapus nama."""
	naran = forms.CharField(max_length=80, required=False, label="Naran")

	def clean_naran(self):
		naran = ' '.join(self.cleaned_data.get('naran', '').split())
		if naran and not naran_valid(naran):
			raise forms.ValidationError('err_name_invalid')
		return rapikan_naran(naran)
