# Lian Timor - Belajar Bahasa Timor Leste

Aplikasi web belajar bahasa untuk semua usia (anak sekolah sampai ibu di pasar). Django + HTML + CSS + JavaScript,
mobile first, bisa dipasang di layar utama HP (PWA). Struktur folder, gaya models/views, dekorator, `layout.html`,
`navbar.html` dan menu mengikuti proyek **SJDF**.

## Struktur folder

```
lian_timor/
├── manage.py
├── lian_timor/            settings.py, urls.py, wsgi.py, asgi.py   (paket proyek, seperti sjdf/sjdf)
├── config/                decorators.py (APA ADANYA dari SJDF), utils.py (upload_to), user_utils.py (group, kontak, buat_user),
│                          i18n.py (semua teks 4 bahasa), templatetags/lian_tags.py
├── custom/                data master: Bahasa, Level, Materi, KarakterAI  + seed_awal, buat_admin
├── main/                  home, login, logout, tamu, PWA
│   ├── static/main/       css (bootstrap, main.css), js, font-awesome, images (tais.svg, lafaek.svg), icons, fonts
│   └── templates/         main/{layout,navbar,adm,kontributor,pelajar,segera}.html, home/{home,login,logout,offline,403,404,500}.html
├── users/                 Perfil (OneToOne ke User), daftar, "Kamu siapa?", akun, daftar utilizador   (auth_utils.py, forms.py)
├── belajar/               Kalimat, ProgresBelajar            (halaman belajar: menyusul)
├── crowdsource/           RekamanSuara                       (halaman rekam: menyusul)
├── ai/                    ai_chat                            (menyusul)
└── report/                admin_dashboard (jumlah user, suara per bahasa, grafik batang)
```

## Group (setiap user dibatasi group, pola `@allowed_users`)

| Group | Boleh |
|---|---|
| `admin` | semuanya: Relatóriu, Utilizadór (matikan/aktifkan), Admin Django (setujui/tolak suara, kelola level/kalimat/karakter AI) |
| `kontributor` | belajar, bicara dengan AI, **crowdsource (rekam suara)** |
| `pelajar` | belajar, bicara dengan AI. Daftar baru dan akun tamu masuk group ini. Kartu "Ajuda AI" menampilkan penjelasan, bukan fitur rekam |

Admin menaikkan user menjadi `kontributor` lewat Admin Django (Users, ubah Groups). **Satu group per user**: `allowed_users`
hanya membaca group pertama, sama seperti di SJDF.

## Menjalankan (Linux Mint / Windows)

```bash
cd lian_timor
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env
python manage.py migrate
python manage.py seed_awal        # 3 group, 33 bahasa, 5 level, 3 karakter AI
python manage.py buat_admin admin@contoh.com      # admin pertama (kata sandi diminta)
python manage.py runserver
```
Buka http://127.0.0.1:8000/ . Tes: `python manage.py test`. **Node tidak diperlukan** (Bootstrap, jQuery, Font Awesome sudah ada di `main/static/main/`).

> Pakai `buat_admin`, bukan `createsuperuser`: superuser biasa tidak punya group, sehingga `@allowed_users` menampilkan halaman 404.

## Tampilan & menu
- **Warna**: merah, kuning, hitam, putih (bendera & tais), tanpa biru. Variabel CSS memakai nama dari contoh SJDF (`--navy`, `--navy-dk`) tetapi
  **nilainya** warna Timor-Leste. Untuk kembali ke hijau SJDF, ubah `--navy` menjadi `#00B050` di `main/static/main/css/main.css`.
- **Topbar** = pita tais (SVG buatan sendiri) di semua halaman; **navbar** + menu desktop; **sidebar HP 72 px** (icon + label) dari CSS SJDF.
- **Menu desktop mulai 1200 px** (menu admin ada 7 item). Di bawah itu: hamburger + sidebar.
- **Ganti bahasa 1 klik** (TET / EN / PT / ID) di pojok atas. Setiap teks ditulis 4 kali di HTML dan CSS menampilkan yang dipilih
  (`{% t "kunci" %}`), jadi instan dan tetap jalan offline. Pesan sistem juga 4 bahasa (`{% pesan message %}`).
- **Tombol BICARA**: buaya ramah di tengah bawah (`.fab-bicara`).
- **PWA**: halaman yang sudah dibuka tetap tampil saat offline; halaman `/admin`, `/users`, `/report`, login tidak disimpan di cache.
  Naikkan `PWA_VERSI` di `settings.py` setiap berkas statis berubah. Service worker hanya aktif di HTTPS atau localhost.

## Yang perlu Anda tahu (jujur)
1. **Bootstrap 4, bukan Tailwind.** `layout.html` dan menu contoh Anda memakai Bootstrap; menggabungkan Tailwind akan bentrok (reset CSS ganda) dan
   menambah berat cache offline. Kalau Anda tetap ingin Tailwind, bilang, tampilannya perlu ditulis ulang.
2. **Teks Tetun dan Portugis di `config/i18n.py` adalah draf AI**, perlu dicek penutur asli. Label admin (`verbose_name`) memakai Tetun dengan gaya SJDF; cek juga.
3. `@allowed_users` (dipakai apa adanya) menampilkan template 404 dengan **status HTTP 200**, bukan 403.
4. **Nomor HP tidak diverifikasi** (SMS OTP butuh layanan berbayar). Akun tamu ("Kontinua la regista") dibatasi 30 per jam per alamat IP.
5. **Login Google/Facebook belum ada** (butuh kunci dari akun Anda).
6. **Privasi suara**: `RekamanSuara` hanya menyimpan bahasa, kalimat, file suara, gaya bicara, dan `pengirim_kode` (kode acak, bukan relasi akun).
   Kode yang sama ada di `users.Perfil.kode_anonim`, jadi pemegang seluruh database tetap bisa menghubungkannya: batasi akses database
   dan jangan ikutkan kolom itu saat mengekspor data pelatihan.
7. Tombol "Dengar" nanti memakai suara bawaan HP bila ada; HP umumnya **tidak punya suara Tetun** → rekam penutur asli lalu unggah di Admin.

## Status
| Bagian | Status |
|---|---|
| Struktur SJDF, `config/decorators.py`, group, models (User, Bahasa, Level, Materi, Kalimat, RekamanSuara, + KarakterAI, Perfil, ProgresBelajar) | Selesai, 39 tes lulus |
| `layout.html`, `navbar.html`, menu per group, topbar tais, 4 bahasa, tombol buaya, PWA | Selesai |
| `home.html`, `login.html` (email/HP + password, tamu), daftar, "Kamu siapa?", akun, daftar utilizador | Selesai |
| `admin_dashboard.html` (user, suara per bahasa, grafik) + Admin Django (dengar, setujui/tolak, matikan pengirim) | Selesai (dasar) |
| `belajar.html` (20 kalimat/level, dengar, rekam saya, progress bar) | Belum. Butuh isi kalimat dari penutur asli |
| `crowdsource.html` (rekam, dengar ulang, kirim, penghitung per bahasa) | Belum |
| `ai_chat.html` (3 karakter, rekam, jawab suara + teks) | Belum |
