from django.urls import path

from . import views

urlpatterns = [
	path('', views.AiChat, name='ai-chat'),
	path('bicara/', views.Bicara, name='ai-bicara'),
	path('riwayat/', views.Riwayat, name='ai-riwayat'),
	path('hapus/', views.Hapus, name='ai-hapus'),
	path('tts/', views.Tts, name='ai-tts'),
	path('suara/', views.SuaraAdmin, name='ai-suara'),
]
