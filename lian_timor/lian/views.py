from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache

from .models import Level


def home(request):
    levels = list(Level.objects.filter(aktif=True))
    return render(request, "home.html", {"levels": levels, "target": Level.TARGET_KALIMAT})


def segera(request):
    """Halaman sementara untuk fitur yang belum dibuat (supaya tombol menu tidak 404)."""
    return render(request, "segera.html")


def offline(request):
    return render(request, "offline.html")


# ---------------------------------------------------------------- PWA
def manifest(request):
    return HttpResponse(render_to_string("pwa/manifest.webmanifest"), content_type="application/manifest+json")


@never_cache
def service_worker(request):
    """Harus dilayani dari akar situs (/sw.js) agar cakupannya seluruh aplikasi."""
    js = render_to_string("pwa/sw.js", {"versi": settings.PWA_VERSI})
    resp = HttpResponse(js, content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    return resp
