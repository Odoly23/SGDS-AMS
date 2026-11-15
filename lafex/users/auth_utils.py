from users.models import Perfil


def c_user_perfil(user):
	"""Perfil milik user (atau '' bila belum ada). Pola sama dengan c_user_fun di SJDF."""
	objects = Perfil.objects.filter(user=user).select_related('user').first()
	obj = ""
	if objects: obj = objects
	return obj
