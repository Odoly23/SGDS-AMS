from django.urls import path

from . import views

urlpatterns = [
	path('', views.Dash, name='report-dash'),
]
