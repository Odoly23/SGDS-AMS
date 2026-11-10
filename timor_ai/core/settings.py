"""
Pengaturan (settings) LAFEX-AI.
Semua nilai rahasia dibaca dari file .env supaya tidak masuk ke Git.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default="0"):
    return os.getenv(name, default).lower() in ("1", "true", "yes")


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-ganti-di-produksi")
DEBUG = env_bool("DJANGO_DEBUG", "1")
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    # app kita
    "chat",
    "datasets",
    "rag",
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

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# ---------- Database ----------
if os.getenv("DB_ENGINE", "postgres") == "sqlite":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "lafex_ai"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "id"          # bahasa antarmuka admin
TIME_ZONE = "Asia/Dili"       # zona waktu Timor-Leste (UTC+9)
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"          # tempat file PDF/TXT upload disimpan
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "chat-page"
LOGOUT_REDIRECT_URL = "login"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

# ---------- Pengaturan AI ----------
LAFEX_AI = {
    "LLM_BACKEND": os.getenv("LLM_BACKEND", "dummy"),            # dummy | hf
    "LLM_MODEL_ID": os.getenv("LLM_MODEL_ID", "google/gemma-2-2b-it"),
    "LLM_LORA_PATH": os.getenv("LLM_LORA_PATH", ""),             # folder adapter LoRA hasil training
    "HF_TOKEN": os.getenv("HF_TOKEN", ""),
    "MAX_NEW_TOKENS": int(os.getenv("LLM_MAX_NEW_TOKENS", "300")),
    "EMBEDDING_BACKEND": os.getenv("EMBEDDING_BACKEND", "hash"),  # hash | sentence-transformers
    "EMBEDDING_MODEL_ID": os.getenv("EMBEDDING_MODEL_ID", "intfloat/multilingual-e5-small"),
    "RAG_TOP_K": 4,
    "RAG_MIN_SCORE": 0.15,       # di bawah ini dianggap "tidak relevan"
    "CHUNK_SIZE": 800,           # jumlah karakter per potongan dokumen
    "CHUNK_OVERLAP": 100,
}
