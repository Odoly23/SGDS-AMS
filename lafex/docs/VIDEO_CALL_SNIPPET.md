# Halaman Video Call LAFEX

Sudah terpasang di aplikasi (bukan lagi contoh tiruan):
- Halaman: `/video-call/` (`ai/templates/ai/video_call.html`, view `ai.views.VideoCall`).
- API: `POST /api/lafex-chat/` (`ai.views.LafexChat`) memakai `proses_giliran()` yang SAMA dengan chat biasa:
  jatah harian (40/hari, tamu 10), batas 8/menit, riwayat percakapan, backend `AI_BACKEND` (`dummy` | `local` Gemma/Qwen via Ollama/vLLM | `anthropic`).
  Giliran yang gagal tidak dihitung.
- Tautan dari halaman Siswa:
```html
<a href="/video-call/?mode=preman&bahasa=tetun&topik=perkenalan&menit=5">Bicara dengan LAFEX</a>
```
`mode`: `preman` | `pintar` | `professional`; `bahasa`: `tetun` | `portugues` | `inggris` | `indonesia`; `topik`: teks pendek; `menit`: 1-15 (bawaan 5).

## Layar utama tanpa menu ("tidak klik ke mana-mana")
Untuk **pelajar** (semua orang, termasuk tamu) beranda `/` langsung masuk ke `/video-call/`. Di satu layar itu ada pilihan bahasa, topik (dari Level), mode, dan durasi, **diingat** di HP (localStorage), jadi pemakai berikutnya cukup menekan **satu** tombol "MULAI PANGGILAN". Menu kecil ☰ (Belajar, Akun, Sai kontributór, Keluar) membuka lembar di halaman yang sama. Tombol 📞 Tutup hanya mengakhiri panggilan (tetap di halaman). Kontributor dan admin tetap punya beranda dan menu lengkap.
Matikan dengan `HOME_LANGSUNG_BICARA=0` di `.env` (kembali ke beranda berisi kartu menu).
Satu ketukan tetap perlu: browser tidak mengizinkan mikrofon/suara menyala sendiri tanpa sentuhan pengguna.

## Pemetaan mode ke karakter AI
| Mode | Karakter | Tambahan perintah (ditulis di server) |
|---|---|---|
| PREMAN | AI Bandidu (`preman`) | gaul dan santai, tetap sopan |
| PINTAR | AI Respeitozu (`sopan`) | guru sabar: koreksi SATU per SATU, minta mengulang |
| PROFESSIONAL | AI Matenek (`profesional`) | formal, seperti latihan wawancara kerja |

`benar` = jawaban tanpa koreksi (model tidak menemukan kesalahan). Topik dibersihkan (huruf/angka/spasi/strip) sebelum masuk ke prompt.

## Cara kerja tangan bebas
Satu sentuhan "MULAI PANGGILAN" (syarat browser untuk mikrofon & suara), lalu: mikrofon menyala otomatis -> kalimat selesai dikirim
-> LAFEX menjawab (mikrofon dimatikan saat LAFEX bicara supaya tidak mendengar suaranya sendiri) -> mikrofon menyala lagi,
sampai hitung mundur habis atau user menutup. Diam 15 detik: LAFEX memancing (maks. 2 kali berturutan). Tombol 🎤 mematikan/menyalakan
mikrofon; kolom ketik tetap bisa dipakai.

## Gambar
Dicari di `/static/img/lafex/{preman,pintar,pro}_{diam,ngomong,jempol,mikir}.png` (ubah `data-img` lewat `{% static %}` bila lokasinya lain).
Bila belum ada, dipakai maskot lafaek bawaan LAFEX (SVG) dengan aksesori sesuai mode.

## Catatan jujur
- **Ini bukan video**, melainkan pergantian gambar + animasi mulut 180 ms.
- **Suara**: SpeechSynthesis browser tidak punya suara Tetun; Tetun dibacakan dengan suara Portugis (pt-PT), pelafalan tidak sempurna.
  Pengenalan suara (SpeechRecognition) juga memakai pt-PT untuk Tetun, jadi ucapan Tetun sering salah dengar. Solusi nyata: Whisper (STT) + XTTS (TTS) di server.
- **Pakai headset**: tanpa headset, mikrofon bisa mendengar suara LAFEX dari speaker.
- **Browser**: tangan bebas butuh `SpeechRecognition` (Chrome/Edge Android & desktop). Di iPhone Safari pengenalan suara sering berhenti/meminta izin
  berulang; bila gagal berulang, mikrofon otomatis dimatikan dan user bisa menekan 🎤 atau mengetik. Butuh HTTPS. Audio ucapan bisa dikirim ke vendor browser.
- **Waktu panggilan** dihitung di browser (pelindung biaya yang sebenarnya adalah jatah harian di server). **Poin** hanya tampilan (localStorage), mudah diubah user.
- Belum diuji di HP sungguhan dan belum dengan model sungguhan; tes memakai mikrofon/suara palsu dan backend demo.
