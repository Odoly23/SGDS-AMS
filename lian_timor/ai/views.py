from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from config.decorators import allowed_users
from config.user_utils import SEMUA_GRUP, nama_grup


@login_required
@allowed_users(allowed_roles=SEMUA_GRUP)
def AiChat(request):
	context = {'group': nama_grup(request.user), 'page': 'ai', 'title': "Ko'alia ho AI"}
	return render(request, 'main/segera.html', context)    # ai_chat.html menyusul
