from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from config.decorators import allowed_users
from config.user_utils import GRUP_ADMIN, GRUP_KONTRIBUTOR, SEMUA_GRUP, nama_grup


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
def CrowdsourceHome(request):
	"""Hanya group kontributor (dan admin) yang boleh merekam. Group lain melihat penjelasan cara menjadi kontributor."""
	group = nama_grup(request.user)
	context = {'group': group, 'page': 'crowdsource', 'title': 'Ajuda AI'}
	if group not in (GRUP_ADMIN, GRUP_KONTRIBUTOR):
		return render(request, 'crowdsource/info.html', context)
	return render(request, 'main/segera.html', context)    # crowdsource.html (rekam suara) menyusul
