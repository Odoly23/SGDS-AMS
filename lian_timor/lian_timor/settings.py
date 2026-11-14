"""Pengaturan Lian Timor. Nilai rahasia dibaca dari file .env."""
import os
from pathlib import Path

from dotenv import load_dotenv
from django.contrib.messages import constants as messages

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-ganti-di-produksi")
DEBUG = os.getenv("DJANGO_DEBUG", "1").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

INSTALLED_APPS = [
	"django.contrib.admin",
	"django.contrib.auth",
	"django.contrib.contenttypes",
	"django.contrib.sessions",
	"django.contrib.messages",
	"django.contrib.staticfiles",
	# app Lian Timor (struktur mengikuti SJDF)
	"config",
	"custom",
	"main",
	"users",
	"belajar",
	"crowdsource",
	"ai",
	"report",
]

MIDDLEWARE = [
	"django.middleware.security.SecurityMiddleware",
	"django.contrib.sessions.middleware.SessionMiddleware",
	"django.middleware.common.CommonMiddleware",
	"django.middleware.csrf.CsrfViewMiddleware",
	"django.contrib.auth.middleware.AuthenticationMiddleware",
	"django.contrib.messages.middleware.MessageMiddleware",
	"django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "lian_timor.urls"
WSGI_APPLICATION = "lian_timor.wsgi.application"

TEMPLATES = [
	{
		"BACKEND": "django.template.backends.django.DjangoTemplates",
		"DIRS": [],
		"APP_DIRS": True,     # template ada di dalam tiap app (main/templates/main/layout.html, dst.)
		"OPTIONS": {
			"context_processors": [
				"django.template.context_processors.request",
				"django.contrib.auth.context_processors.auth",
				"django.contrib.messages.context_processors.messages",
			],
		},
	},
]

if os.getenv("DB_ENGINE", "sqlite") == "postgres":
	DATABASES = {
		"default": {
			"ENGINE": "django.db.backends.postgresql",
			"NAME": os.getenv("DB_NAME", "lian_timor"),
			"USER": os.getenv("DB_USER", "postgres"),
			"PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
			"HOST": os.getenv("DB_HOST", "127.0.0.1"),
			"PORT": os.getenv("DB_PORT", "5432"),
		}
	}
else:
	DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_PASSWORD_VALIDATORS = [
	{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
	{"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 60      # 60 hari: akun tamu & HP pribadi tidak perlu masuk berulang
MESSAGE_TAGS = {messages.ERROR: "danger"}    # supaya cocok dengan kelas Bootstrap alert-danger

LANGUAGE_CODE = "id"        # hanya untuk Admin Django; bahasa aplikasi diatur sendiri (config/i18n.py)
TIME_ZONE = "Asia/Dili"
USE_I18N = False
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SUARA_MAKS_BYTE = 2 * 1024 * 1024            # batas unggah suara crowdsource (2 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024
PWA_VERSI = "v2"                             # naikkan setiap berkas statis berubah (memperbarui cache offline di HP)
