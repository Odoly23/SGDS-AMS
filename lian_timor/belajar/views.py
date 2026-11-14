from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from config.decorators import allowed_users
from config.user_utils import SEMUA_GRUP, nama_grup


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
def BelajarList(request):
	context = {'group': nama_grup(request.user), 'page': 'belajar', 'title': 'Aprende'}
	return render(request, 'main/segera.html', context)    # belajar.html menyusul
