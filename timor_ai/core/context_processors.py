from django.conf import settings


def features(request):
    """Variabel yang tersedia di semua template."""
    return {"FACEBOOK_ENABLED": settings.FACEBOOK_ENABLED}
