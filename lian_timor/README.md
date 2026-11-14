# Lian Timor - Belajar Bahasa Timor Leste

Aplikasi web belajar bahasa untuk semua usia (anak sekolah sampai ibu di pasar). Django + HTML + Tailwind CSS + JavaScript,
mobile first, bisa dipasang di layar utama HP (PWA).

## Status: tahap 1 dari 3

| Bagian | Status |
|---|---|
| `models.py` (Pengguna, Bahasa, Level, Materi, Kalimat, KarakterAI, RekamanSuara, ProgresBelajar) | **Selesai**, 20 tes lulus |
| `base.html`: topbar tais, ganti 4 bahasa 1 klik, menu bawah, tombol buaya | **Selesai** |
| `home.html` (4 menu besar + "Hari ini belajar apa?") | **Selesai** |
| PWA: manifest, ikon, service worker, halaman offline | **Selesai**, offline diuji di Chromium |
| Admin dasar (kelola semua model, setujui/tolak suara, matikan pengguna) | **Selesai** (dasar) |
| `login.html`, `ai_chat.html`, `belajar.html`, `crowdsource.html`, `admin_dashboard.html` | **Belum.** Tombolnya menampilkan "Sei mai lalais / Segera hadir" |
| Isi 100 kalimat (5 level x 20) | **Belum.** Harus ditulis/diverifikasi penutur asli |

## Menjalankan (Linux Mint / Windows)

```bash
cd lian_timor
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env
python manage.py migrate
python manage.py seed_awal        # 33 bahasa, 5 level, 3 karakter AI
python manage.py createsuperuser
python manage.py runserver
```
Buka http://127.0.0.1:8000/ (aplikasi) dan http://127.0.0.1:8000/admin/ (admin). Tes: `python manage.py test`.

CSS Tailwind sudah dikompilasi dan disertakan (`static/css/tailwind.css`), jadi **Node tidak wajib** untuk menjalankan.
Hanya jika Anda mengubah template/gaya: `npm install` lalu `npm run build:css`.

## Cara kerja yang perlu dipahami

- **Ganti bahasa tanpa memuat ulang.** Setiap teks ditulis 4 kali di HTML (`<span data-l="tet">…`), CSS hanya menampilkan yang
  sesuai `<html lang>`. Pilihan disimpan di HP. Cara ini membuat ganti bahasa instan dan tetap jalan saat offline.
  Teks antarmuka ada di `lian/i18n.py`; teks dari database (judul Level, kalimat) lewat `{% ml objek "judul" %}`.
- **Motif tais** adalah SVG buatan sendiri (`static/img/tais.svg`, ubin 48x64 diulang), bukan foto. Warna: merah, kuning, hitam, putih.
- **Ikon buaya** (`static/img/lafaek.svg`): lafaek ramah dan tersenyum. Dipakai di tombol Bicara, kartu menu, ikon aplikasi.
- **Offline (PWA).** Halaman yang sudah dibuka tersimpan; halaman baru saat offline menampilkan "La iha internet". Halaman
  `/admin`, `/akun`, `/masuk` sengaja TIDAK disimpan (HP sering dipakai bergantian). Naikkan `PWA_VERSI` di `config/settings.py`
  setiap kali file statis berubah. Service worker hanya aktif di HTTPS atau localhost.
- **Karakter AI** (Preman/Sopan/Profesional) tersimpan di database; Admin bisa mengubah nama, deskripsi, dan instruksi AI
  (`prompt_sistem`) tanpa menyentuh kode. `seed_awal` tidak menimpa teks yang sudah diubah Admin. Aturan "tidak menghina" untuk
  AI Preman sudah ada di instruksinya.

## Hal yang harus Anda tahu (jujur)

1. **Terjemahan Tetun dan Portugis di antarmuka adalah draf AI.** Mohon dicek penutur asli (edit di `lian/i18n.py`).
2. **Tidak ada audio contoh.** Tombol "Dengar" nanti memakai suara bawaan HP bila ada, tetapi HP umumnya **tidak punya suara Tetun**.
   Untuk Tetun, rekam penutur asli lalu unggah di Admin (kolom `audio_tet`).
3. **Nomor HP tidak diverifikasi** (verifikasi SMS butuh layanan berbayar). Nomor hanya pengenal login bersama password.
4. **Login Google/Facebook** butuh akun pengembang dan kunci dari Anda (Google Cloud Console / Meta for Developers); belum dibuat.
5. **Privasi crowdsource.** `RekamanSuara` hanya menyimpan bahasa, kalimat, file suara, gaya bicara, dan `pengirim_kode`.
   `pengirim_kode` adalah kode acak (bukan relasi ke akun) agar Admin bisa memblokir pengirim nakal. Karena kode yang sama juga ada
   di tabel Pengguna, **orang yang memegang seluruh database tetap bisa menghubungkannya**. Batasi akses database dan jangan
   ikutkan kolom itu saat mengekspor data untuk melatih AI.
6. Daftar bahasa daerah memakai ejaan yang sudah dikoreksi; 10 nama ditandai "perlu verifikasi" (cek ke INL-UNTL). Lihat
   README proyek LAFEX-AI bagian 2.

## Rencana tahap berikutnya (urutan yang saya sarankan)
1. `login.html` (email/HP + password, tamu, "Kamu siapa?") dan Google/Facebook bila kunci sudah ada.
2. `belajar.html` + isi 20 kalimat Level 1 (dicek penutur asli), tombol Dengar/Rekam, progress bar.
3. `crowdsource.html`: rekam dengan MediaRecorder, dengar ulang, kirim, penghitung suara per bahasa.
4. `ai_chat.html`: rekam suara, jawaban teks + suara (Tetun + Inggris), 3 karakter AI.
5. `admin_dashboard.html`: jumlah user, suara per bahasa, grafik, dengar-setujui-tolak di satu layar.
