from django.urls import path

from . import views

urlpatterns = [
	path('', views.BelajarList, name='belajar-list'),
]
