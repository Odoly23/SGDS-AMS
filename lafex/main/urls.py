from django.urls import path

from . import views

urlpatterns = [
	path('', views.Home, name='home'),
	path('login/', views.Login, name='login'),
	path('logout/', views.Logout, name='logout'),
	path('tamu/', views.Tamu, name='tamu'),
	path('offline/', views.Offline, name='offline'),
	path('manifest.webmanifest', views.Manifest, name='manifest'),
	path('sw.js', views.ServiceWorker, name='sw'),
]
