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
    "django.contrib.sites",          # dibutuhkan allauth
    "rest_framework",
    # login email + Facebook
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.facebook",
    # app kita
    "chat",
    "datasets",
    "rag",
    "billing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
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
                "core.context_processors.features",
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

# ---------- Login: email + Facebook (django-allauth) ----------
SITE_ID = 1
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",            # admin (username)
    "allauth.account.auth_backends.AuthenticationBackend",  # user biasa (email)
]
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "chat-page"
ACCOUNT_LOGOUT_REDIRECT_URL = "account_login"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
# "mandatory" = wajib klik link di email dulu (mencegah email palsu menyedot poin gratis).
# Saat belajar/lokal bisa diubah ke "optional" lewat .env
ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "mandatory")
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_RATE_LIMITS = {"login_failed": "5/5m"}   # tahan tebak-tebak password
SOCIALACCOUNT_QUERY_EMAIL = True                 # minta email dari Facebook; kalau kosong, user diminta mengisi

FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
FACEBOOK_ENABLED = bool(FACEBOOK_APP_ID and FACEBOOK_APP_SECRET)
SOCIALACCOUNT_PROVIDERS = {
    "facebook": {
        "SCOPE": ["email", "public_profile"],
        "METHOD": "oauth2",
        **({"APP": {"client_id": FACEBOOK_APP_ID, "secret": FACEBOOK_APP_SECRET, "key": ""}} if FACEBOOK_ENABLED else {}),
    }
}

# Email verifikasi: lokal -> tampil di terminal; produksi -> isi SMTP di .env
if os.getenv("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

# ---------- Pengaturan AI ----------
LAFEX_AI = {
    "LLM_BACKEND": os.getenv("LLM_BACKEND", "dummy"),            # dummy | hf | anthropic
    "LLM_MODEL_ID": os.getenv("LLM_MODEL_ID", "google/gemma-2-2b-it"),
    "LLM_LORA_PATH": os.getenv("LLM_LORA_PATH", ""),             # folder adapter LoRA hasil training
    "HF_TOKEN": os.getenv("HF_TOKEN", ""),
    "LLM_DTYPE": os.getenv("LLM_DTYPE", "bfloat16"),             # bfloat16 | float16 | float32
    "MAX_NEW_TOKENS": int(os.getenv("LLM_MAX_NEW_TOKENS", "300")),
    "EMBEDDING_BACKEND": os.getenv("EMBEDDING_BACKEND", "hash"),  # hash | sentence-transformers
    "EMBEDDING_MODEL_ID": os.getenv("EMBEDDING_MODEL_ID", "intfloat/multilingual-e5-small"),
    # --- Model berbayar lewat API (LLM_BACKEND=anthropic). Kunci API hanya di server, TIDAK PERNAH ke browser ---
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
    "ANTHROPIC_MODEL": os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5"),
    "ANTHROPIC_EFFORT": os.getenv("ANTHROPIC_EFFORT", "low"),     # low = paling hemat; kosongkan jika model tidak mendukung
    "ANTHROPIC_MAX_TOKENS": int(os.getenv("ANTHROPIC_MAX_TOKENS", "2048")),  # termasuk token "berpikir"
    "RAG_TOP_K": 4,
    "RAG_MIN_SCORE": 0.15,       # di bawah ini dianggap "tidak relevan"
    "CHUNK_SIZE": 800,           # jumlah karakter per potongan dokumen
    "CHUNK_OVERLAP": 100,
}

# ---------- Poin & tagihan ----------
# 1 poin = 1/POINTS_PER_USD dolar. Harga token = harga model yang Anda bayar (USD per 1 juta token).
# Isi PRICE_* sesuai model di ANTHROPIC_MODEL (cek halaman harga Anthropic); MARGIN = pengali keuntungan/biaya server.
BILLING = {
    "POINTS_PER_USD": int(os.getenv("POINTS_PER_USD", "1000")),
    "PRICE_IN_PER_M": float(os.getenv("PRICE_IN_PER_M", "4.0")),    # contoh: Opus 5.5 = $4 / 1 juta token masuk
    "PRICE_OUT_PER_M": float(os.getenv("PRICE_OUT_PER_M", "20.0")),  # contoh: Opus 5.5 = $20 / 1 juta token keluar
    "MARGIN": float(os.getenv("BILLING_MARGIN", "3.0")),
    "MIN_CHARGE": 1,
    "MIN_BALANCE_TO_CHAT": int(os.getenv("MIN_BALANCE_TO_CHAT", "20")),
    "TRIAL_CREDITS": int(os.getenv("TRIAL_CREDITS", "100")),         # poin gratis untuk user baru (biaya Anda!)
    "MAX_MESSAGES_PER_MINUTE": int(os.getenv("MAX_MESSAGES_PER_MINUTE", "10")),
}
