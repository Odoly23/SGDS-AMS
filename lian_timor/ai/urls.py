from django.urls import path

from . import views

urlpatterns = [
	path('', views.AiChat, name='ai-chat'),
]
