from django.urls import path

from . import views

urlpatterns = [
	path('register/', views.Register, name='register'),
	path('peran/', views.Peran, name='user-peran'),
	path('account/', views.Account, name='user-account'),
	path('list/', views.UserList, name='u-list'),
	path('toggle/<int:pk>/', views.UserToggle, name='u-toggle'),
]
