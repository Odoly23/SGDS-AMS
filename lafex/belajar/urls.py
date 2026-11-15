from django.urls import path

from . import views

urlpatterns = [
	path('', views.BelajarList, name='belajar-list'),
	path('nivel/<int:nomor>/', views.BelajarLevel, name='belajar-level'),
	path('progresu/<int:pk>/', views.ProgresSimpan, name='belajar-progres'),
]
