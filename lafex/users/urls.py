from django.urls import path

from . import views

urlpatterns = [
	path('register/', views.Register, name='register'),
	path('peran/', views.Peran, name='user-peran'),
	path('account/', views.Account, name='user-account'),
	path('list/', views.UserList, name='u-list'),
	path('toggle/<int:pk>/', views.UserToggle, name='u-toggle'),
	path('ajukan/', views.Ajukan, name='user-ajukan'),
	path('pengajuan/', views.Pengajuan, name='u-pengajuan'),
	path('pengajuan/<int:pk>/', views.PengajuanAksi, name='u-pengajuan-aksi'),
]
