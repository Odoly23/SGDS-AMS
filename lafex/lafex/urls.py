from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
	path("admin/", admin.site.urls),
	path("", include("main.urls")),
	path("users/", include("users.urls")),
	path("belajar/", include("belajar.urls")),
	path("ai/", include("ai.urls")),
	path("crowdsource/", include("crowdsource.urls")),
	path("report/", include("report.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "main.views.error_403"
handler404 = "main.views.error_404"
handler500 = "main.views.error_500"
