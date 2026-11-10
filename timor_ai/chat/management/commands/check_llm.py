"""
Memeriksa kesiapan model AI langkah demi langkah dan memberi petunjuk perbaikan.

  python manage.py check_llm                 # cek semuanya + tes jawab singkat
  python manage.py check_llm --skip-generate # hanya cek token/lisensi/memori (tanpa unduh model besar)
"""
import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand


def ok(msg):
    return f"  [OK]    {msg}"


def bad(msg):
    return f"  [GAGAL] {msg}"


def ram_gb():
    """Total RAM dalam GB (Linux/Mac lewat sysconf, Windows lewat ctypes). None jika tak bisa dibaca."""
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3
    except (ValueError, OSError, AttributeError):
        pass
    try:
        import ctypes

        class MEMSTAT(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MEMSTAT()
        m.dwLength = ctypes.sizeof(MEMSTAT)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullTotalPhys / 1024**3
    except Exception:  # noqa: BLE001
        return None


class Command(BaseCommand):
    help = "Cek kesiapan Gemma 2 (token, lisensi, memori, tes jawab)."

    def add_arguments(self, parser):
        parser.add_argument("--skip-generate", action="store_true")

    def handle(self, *args, **opts):
        cfg = settings.LAFEX_AI
        problems = 0
        w = self.stdout.write

        w("1) Konfigurasi (.env)")
        if cfg["LLM_BACKEND"] != "hf":
            w(bad(f"LLM_BACKEND={cfg['LLM_BACKEND']!r}. Ubah menjadi LLM_BACKEND=hf di file .env"))
            problems += 1
        else:
            w(ok(f"LLM_BACKEND=hf, model={cfg['LLM_MODEL_ID']}, dtype={cfg['LLM_DTYPE']}"))
        if not cfg["HF_TOKEN"]:
            w(bad("HF_TOKEN kosong. Buat token di https://huggingface.co/settings/tokens (tipe Read) lalu isi di .env"))
            problems += 1
        else:
            w(ok("HF_TOKEN terisi"))

        w("2) Paket Python")
        try:
            import torch
            import transformers

            w(ok(f"torch {torch.__version__}, transformers {transformers.__version__}"))
        except ImportError as exc:
            w(bad(f"{exc.name} belum terpasang. Jalankan: pip install -r requirements-ai.txt (torch dulu, lihat README)"))
            self.stdout.write(self.style.ERROR(f"\n{problems + 1} masalah. Perbaiki lalu jalankan lagi."))
            return

        w("3) Perangkat keras")
        ram = ram_gb()
        has_cuda = torch.cuda.is_available()
        if has_cuda:
            w(ok(f"GPU: {torch.cuda.get_device_name(0)} ({torch.cuda.get_device_properties(0).total_memory / 1024**3:.0f} GB VRAM)"))
        else:
            w(ok("Tidak ada GPU -> jalan di CPU (jawaban lambat, beberapa detik per kata)"))
        if ram is not None:
            need = 6 if cfg["LLM_DTYPE"] != "float32" else 11
            w((ok if ram >= need else bad)(f"RAM {ram:.1f} GB (butuh sekitar {need} GB bebas untuk Gemma 2 2B)"))
            problems += ram < need and not has_cuda

        w("4) Akses ke model (lisensi Gemma)")
        try:
            from huggingface_hub import hf_hub_download
            from huggingface_hub.errors import GatedRepoError, HfHubHTTPError, RepositoryNotFoundError

            hf_hub_download(cfg["LLM_MODEL_ID"], "config.json", token=cfg["HF_TOKEN"] or None)
            w(ok("Token & lisensi valid, model bisa diakses"))
        except GatedRepoError:
            w(bad(f"Lisensi belum disetujui. Buka https://huggingface.co/{cfg['LLM_MODEL_ID']} , login, klik 'Acknowledge license'"))
            problems += 1
        except RepositoryNotFoundError:
            w(bad("Model tidak ditemukan / token salah. Periksa LLM_MODEL_ID dan HF_TOKEN"))
            problems += 1
        except Exception as exc:  # noqa: BLE001 - jaringan, dll.
            w(bad(f"Tidak bisa menghubungi Hugging Face: {type(exc).__name__}: {exc}"))
            problems += 1

        if problems or opts["skip_generate"]:
            style = self.style.ERROR if problems else self.style.SUCCESS
            w(style(f"\n{problems} masalah." if problems else "\nPemeriksaan dasar lolos (tes jawab dilewati)."))
            return

        w("5) Tes jawab (unduhan pertama ~5 GB, bisa beberapa menit)")
        from chat import llm

        t0 = time.monotonic()
        answer = llm.generate(
            [{"role": "user", "content": "Jawab dalam bahasa Tetun, satu kalimat pendek: apa ibu kota Timor-Leste?"}],
            max_new_tokens=40,
        )
        w(ok(f"Model menjawab dalam {time.monotonic() - t0:.0f} detik:"))
        w(f"        {answer!r}")
        w(self.style.SUCCESS("\nSelesai. Restart runserver, lalu coba chat. Bahasa lokal masih lemah sebelum ada LoRA."))
