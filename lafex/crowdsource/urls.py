from django.urls import path

from . import views

urlpatterns = [
	path('', views.CrowdsourceHome, name='crowdsource-home'),
	path('berikut/', views.Berikut, name='crowdsource-berikut'),
	path('kirim/', views.Kirim, name='crowdsource-kirim'),
	path('kontribusiku/', views.Kontribusiku, name='crowdsource-mine'),
	path('tinjau/', views.Tinjau, name='crowdsource-tinjau'),
	path('tinjau/<int:pk>/', views.TinjauAksi, name='crowdsource-aksi'),
	path('audio/<int:pk>/', views.Audio, name='crowdsource-audio'),
	path('kontribusiku/<int:pk>/transkripsi/', views.KontribTranskripsi, name='crowdsource-tr'),
	path('tinjau/whisper-semua/', views.WhisperSemua, name='crowdsource-whisper-semua'),
]
