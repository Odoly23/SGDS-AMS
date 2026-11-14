from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import render

from config.decorators import allowed_users
from config.user_utils import GRUP_ADMIN, nama_grup
from django.db.models import Sum
from django.utils import timezone

from ai.models import Giliran
from crowdsource.models import RekamanSuara
from custom.models import Bahasa


@login_required
@allowed_users(allowed_roles=[GRUP_ADMIN])
def Dash(request):
	"""Ringkasan untuk admin: jumlah user, jumlah suara per bahasa, grafik batang sederhana (CSS, tanpa pustaka)."""
	per_bahasa = (Bahasa.objects.annotate(
		total=Count('rekaman'),
		menunggu=Count('rekaman', filter=Q(rekaman__status='menunggu')),
		disetujui=Count('rekaman', filter=Q(rekaman__status='disetujui')),
	).filter(total__gt=0).order_by('-total'))
	maks = max([b.total for b in per_bahasa] or [1])
	for b in per_bahasa:
		b.persen = round(b.total * 100 / maks)
	hari_ini = Giliran.objects.filter(datetime__gte=timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0))
	token = hari_ini.aggregate(m=Sum('token_masuk'), k=Sum('token_keluar'))
	context = {
		'group': nama_grup(request.user), 'page': 'report', 'title': 'Relatóriu jerál',
		'giliran_ai': hari_ini.count(), 'token_ai': (token['m'] or 0) + (token['k'] or 0),
		'jumlah_user': User.objects.filter(is_active=True).count(),
		'jumlah_tamu': User.objects.filter(perfil__is_tamu=True).count(),
		'jumlah_suara': RekamanSuara.objects.count(),
		'menunggu': RekamanSuara.objects.filter(status='menunggu').count(),
		'disetujui': RekamanSuara.objects.filter(status='disetujui').count(),
		'per_bahasa': per_bahasa,
	}
	return render(request, 'report/admin_dashboard.html', context)
