"""Pengaturan LAFEX. Nilai rahasia dibaca dari file .env."""
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
	# app LAFEX (struktur mengikuti SJDF)
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

ROOT_URLCONF = "lafex.urls"
WSGI_APPLICATION = "lafex.wsgi.application"

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
			"NAME": os.getenv("DB_NAME", "lafex"),
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
PWA_VERSI = "v13"                             # naikkan setiap berkas statis berubah (memperbarui cache offline di HP)

# ---------- Percakapan suara dengan AI (ai_chat) ----------
# BACKEND: "dummy" = balasan contoh | "local" = model gratis/open-source (Gemma dll, server Ollama/llama.cpp/vLLM) | "anthropic" = model berbayar lewat API (Anda membayar per token).
# Kunci API HANYA di server (.env), tidak pernah dikirim ke browser.
AI = {
	"BACKEND": os.getenv("AI_BACKEND", "dummy"),
	"ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
	"LOCAL_URL": os.getenv("LOCAL_LLM_URL", "http://127.0.0.1:11434/v1"),   # Ollama bawaan; llama-server: http://127.0.0.1:8080/v1
	"LOCAL_MODEL": os.getenv("LOCAL_LLM_MODEL", "gemma2:2b"),               # nama model di server Anda (mis. hasil LoRA Anda: "lafex-gemma")
	"LOCAL_KUNCI": os.getenv("LOCAL_LLM_KEY", ""),                          # kosong untuk server sendiri
	"LOCAL_SUHU": float(os.getenv("LOCAL_LLM_SUHU", "0.7")),
	"LOCAL_TIMEOUT": int(os.getenv("LOCAL_LLM_TIMEOUT", "60")),
	"MODEL": os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5"),
	"EFFORT": os.getenv("ANTHROPIC_EFFORT", "low"),                 # low = paling hemat; kosongkan bila model tidak mendukung
	"MAX_TOKENS": int(os.getenv("ANTHROPIC_MAX_TOKENS", "1500")),   # termasuk token "berpikir"
	"BATAS_HARI": int(os.getenv("AI_BATAS_HARI", "40")),            # giliran bicara per user per hari (melindungi biaya Anda)
	"BATAS_HARI_TAMU": int(os.getenv("AI_BATAS_HARI_TAMU", "10")),  # akun tamu lebih sedikit
	"BATAS_MENIT": 8,
	"MAKS_TEKS": 500,
	"RIWAYAT_GILIRAN": 6,                                           # berapa giliran terakhir dikirim sebagai konteks
	"RIWAYAT_JAM": 6,                                               # konteks hanya dari 6 jam terakhir
}


# ---------- Suara: Whisper (STT) dan XTTS (TTS) milik sendiri. Kosong = mati. Lihat docs/MELATIH_SUARA.md ----------
SUARA = {
	"STT_URL": os.getenv("STT_URL", ""),                 # mis. http://127.0.0.1:8000/v1  (faster-whisper-server / whisper.cpp / LocalAI)
	"STT_MODEL": os.getenv("STT_MODEL", "whisper-1"),     # nama model di server Anda (mis. hasil fine-tune Tetun Anda)
	"STT_KUNCI": os.getenv("STT_KEY", ""),
	"STT_BAHASA": os.getenv("STT_BAHASA", ""),            # kosong = deteksi otomatis (Whisper bawaan TIDAK punya Tetun)
	"STT_TIMEOUT": int(os.getenv("STT_TIMEOUT", "120")),
	"TTS_URL": os.getenv("TTS_URL", ""),                 # mis. http://127.0.0.1:8020/tts_to_audio/  (xtts-api-server)
	"TTS_SUARA": os.getenv("TTS_SUARA", "lafex"),         # nama/berkas suara pembicara di server XTTS
	"TTS_BAHASA": os.getenv("TTS_BAHASA", "pt"),          # XTTS bawaan tidak punya Tetun: pt = pendekatan, ganti setelah fine-tune
	"TTS_KUNCI": os.getenv("TTS_KEY", ""),
	"TTS_TIMEOUT": int(os.getenv("TTS_TIMEOUT", "60")),
	"TTS_MAKS_TEKS": 300,
	"TTS_BATAS_MENIT": 20,                               # permintaan suara per user per menit (melindungi GPU)
	"WHISPER_BATCH": 15,                                 # maksimal rekaman sekali "Whisper semua"
}

# 1 = pelajar yang masuk dialihkan langsung ke /video-call/ (tanpa halaman Siswa). BAWAAN 0: siswa memilih materi di halaman Siswa,
# lalu menekan "Bicara dengan LAFEX" (satu klik) ke /video-call/?mode=..&bahasa=..&topik=.. .
HOME_LANGSUNG_BICARA = os.getenv("HOME_LANGSUNG_BICARA", "0") == "1"
