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
├── belajar/               Kalimat, ProgresBelajar; halaman Belajar (level, kalimat 4 bahasa, dengar, rekam, progres); seed_level1
├── crowdsource/           RekamanSuara; halaman 'Ajuda AI' (pilih lian, estilu, rekam, kirim); validasi unggahan
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
python manage.py seed_level1      # 20 kalimat Level 1 (DRAF AI, perlu dicek penutur asli)
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

## Halaman Belajar (`/belajar/`)
- **Daftar level**: kartu besar bergambar + progress bar ("Ita aprende ona 5 husi 20").
- **Halaman level**: kalimat dikelompokkan per Materi; tiap kalimat tampil dalam **Tetun, English, Português, Indonesia** + gambar emoji untuk yang belum lancar membaca.
- **Rona (dengar)**: memutar file audio Tetun bila Admin sudah mengunggahnya (Admin > Materi > Kalimat). Tombol kecil EN/PT/ID memakai file audio bila ada, jika tidak memakai
  suara bawaan HP; tombol otomatis mati bila HP tidak punya suara bahasa itu. **Belum ada audio Tetun**, jadi tombol "Rona" mati sampai penutur asli merekamnya (disengaja: HP umumnya tidak punya suara Tetun, dan kami tidak mau memalsukan pengucapan).
- **Grava ha'u (rekam saya)**: latihan mengucapkan; rekaman **hanya di HP, tidak diunggah**.
- **Ha'u aprende ona**: menandai kalimat; progres tersimpan di server. Saat offline, tanda dicatat di HP dan dikirim otomatis begitu internet kembali.
- Kalimat berstatus `draft` menampilkan catatan "belum dicek penutur asli". Ubah status menjadi `terverifikasi` di Admin setelah dicek.

## Halaman Ajuda AI / crowdsource (`/crowdsource/`, hanya group `kontributor` dan `admin`)
1. Pilih **lian rejionál** (Tetun + semua bahasa daerah yang dicentang "Hatudu iha Ajuda AI" di Admin; tiap tombol menampilkan jumlah suara yang sudah terkumpul).
2. Pilih **estilu ko'alia**: Preman / Sopan / Profesional (teksnya diatur Admin).
3. Muncul **1 kalimat** (Tetun besar + arti EN/PT/ID). Kalimat dipilih yang **paling sedikit direkam** untuk bahasa itu dan yang belum pernah direkam user ini (bahasa + gaya sama).
4. Tekan **tombol mikrofon merah besar** untuk merekam, tekan lagi untuk berhenti, **dengar ulang**, lalu **Haruka (kirim)** atau rekam ulang.
5. Muncul "Obrigadu! Ita nia lian ajuda AI Timor!" + penghitung ("Iha lian 1 ona ba Fataluku").
Pilihan bahasa + gaya diingat untuk kunjungan berikutnya.

**Yang disimpan**: bahasa, kalimat, file suara, gaya bicara (+ kode acak pengirim agar Admin bisa memblokir penyalahgunaan). **Tidak diminta**: nama, nomor HP, alamat.
**Pemeriksaan di server**: harus group kontributor/admin; file diperiksa dari **isinya** (tanda webm/ogg/wav/m4a/mp3), bukan dari nama; maks 2 MB; durasi minimal 0,8 detik; satu rekaman per kalimat+bahasa+gaya
per pengirim; maks 10 per menit dan 100 per hari per user; nama berkas diacak. **Admin** mendengar, menyetujui/menolak, mengisi transkripsi, dan bisa mematikan pengirim nakal (Admin > Rekaman Lian).

## Catatan keamanan & operasional
- **Mikrofon hanya jalan di HTTPS atau localhost.** Untuk produksi wajib HTTPS.
- Suara tersimpan di `media/rekaman_suara/`. Django hanya menyajikan `/media/` saat `DEBUG=1`. Di produksi sajikan lewat nginx **dengan akses terbatas untuk admin** (jangan publik): suara adalah data pengguna.
- Cache offline dipisah: **berkas statis** (aman) dan **halaman HTML** (bisa memuat progres user). Cache halaman **dihapus saat logout**, supaya HP yang dipakai bergantian tidak membocorkan progres orang sebelumnya.
- 33 bahasa membuat daftar pilihan cukup panjang; kolom pencarian bisa ditambah nanti.

## Status
| Bagian | Status |
|---|---|
| Struktur SJDF, `config/decorators.py`, group, models | Selesai |
| `layout.html`, `navbar.html`, menu per group, topbar tais, 4 bahasa, tombol buaya, PWA | Selesai |
| `home.html`, `login.html`, daftar, tamu, "Kamu siapa?", akun, daftar utilizador | Selesai |
| **`belajar.html`** (daftar level) dan **`level.html`** (kalimat, dengar, rekam saya, progres, offline) | **Selesai** |
| **`crowdsource.html`** (rekam, dengar ulang, kirim, penghitung) + validasi unggahan + antrean Admin | **Selesai** |
| `admin_dashboard.html` + Admin Django (dengar, setujui/tolak, matikan pengirim) | Selesai (dasar) |
| 20 kalimat Level 1 | Ada, tetapi **DRAF AI** (perlu dicek penutur asli) |
| Level 2-5 (kalimat) | Belum ditulis |
| Audio Tetun untuk kalimat | Belum (butuh rekaman penutur asli) |
| `ai_chat.html` (3 karakter, rekam, jawab suara + teks) | Belum |
| Login Google/Facebook | Belum (butuh kunci dari akun Anda) |
