from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    # halaman di bawah ini akan dibuat bertahap; sementara menampilkan "Segera hadir"
    path("bicara/", views.segera, name="ai_chat"),
    path("belajar/", views.segera, name="belajar"),
    path("bantu-ai/", views.segera, name="crowdsource"),
    path("masuk/", views.segera, name="login"),
    path("akun/", views.segera, name="akun"),
    path("offline/", views.offline, name="offline"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="sw"),
]
