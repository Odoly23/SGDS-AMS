from django.urls import path

from . import views

urlpatterns = [
	path('', views.CrowdsourceHome, name='crowdsource-home'),
	path('berikut/', views.Berikut, name='crowdsource-berikut'),
	path('kirim/', views.Kirim, name='crowdsource-kirim'),
]
