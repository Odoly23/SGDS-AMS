# Halaman Video Call LAFEX (`ai/templates/ai/video_call.html`)

## Alur (satu klik)
1. Di halaman Siswa, siswa memilih Bahasa, Topik, dan Mode **di sana**, lalu menekan **satu** tombol:
```html
<a href="/video-call/?mode=preman&bahasa=tetun&topik=bebas">Bicara dengan LAFEX</a>
```
   `mode`: `preman` | `pintar` | `professional` (atau `pro`); `bahasa`: `tetun` | `portugues` | `inggris` | `indonesia`; `topik`: teks pendek. Tanpa parameter: preman, tetun, bebas.
2. Video Call langsung terbuka: LAFEX besar, LAFEX menyapa **"Bondia! Mai ko'alia!"**, mikrofon menyala sendiri. Siswa tinggal bicara.
3. LAFEX mendengarkan sampai siswa diam **2 detik** (omongan tidak dipotong walau mesin pengenalan suara berhenti sendiri di tengah), baru menjawab.
4. Jawaban benar -> gambar jempol 2 detik. Ada koreksi tata bahasa -> tampil di bawah jawaban.
5. 📞 Tutup -> konfirmasi **"Hakarak hapara? / Mau berhenti?" [Ya] [Belum]** -> kembali ke halaman Siswa.

Mengganti mode/bahasa/topik hanya bisa di halaman Siswa, bukan di layar ini (supaya anak tidak salah pencet).

## Isi layar (tidak ada yang lain)
- Atas: `[☰] [Timer] [Poin]` dan teks kecil tidak bisa diklik: `Tetun • Bebas • PREMAN`. Timer menghitung maju (tidak ada durasi/batas waktu; pelindung biaya adalah jatah harian di server).
- Tengah: gambar LAFEX besar + SATU status: **Lagi Ngomong** (biru) / **Lagi Dengerin... Ko'alia took!** (merah berkedip) / **Lagi Mikir** (kuning) / **Siap** (hijau).
- Bawah video: subtitle 2 baris (apa kata siswa; apa kata LAFEX + koreksi).
- Paling bawah: `[🔊 Ulangi] [🎤 Mute/Unmute] [📞 Tutup]`.
- Tidak ada: pilihan bahasa/topik/durasi/mode, tombol Mulai, kolom ketik. Lencana "demo" hanya tulisan kecil di pojok.
- ☰ membuka menu (Beranda Siswa, Belajar, Akun, Keluar); setiap pindah halaman juga meminta konfirmasi.

## Gambar LAFEX (hanya 12 PNG milik Anda, tidak ada gambar lain)
`/static/img/lafex/{preman,pintar,pro}_{diam,ngomong,jempol,mikir}.png`
Diam = `diam` | Dengerin = `mikir` | Mikir = `mikir` | Ngomong = `ngomong`<->`diam` tiap 180 ms | Benar = `jempol` 2 detik lalu `diam`.
Bila sebuah file tidak ada, dipakai `diam.png` mode itu; bila `diam.png` juga tidak ada, gambar dikosongkan (tanpa emoji/gambar pengganti/internet).

## Suara & pengenalan
- `webkitSpeechRecognition`: `continuous=false`, `interimResults=true`. Hasil sementara dan akhir **digabung**; kirim ke `/api/lafex-chat/` setelah 2 detik tanpa suara baru. Terlalu pendek/tidak jelas (< 3 huruf): LAFEX bilang "Hau la rona ho diak, bele ko'alia fali?" lalu mendengarkan lagi.
- Suara LAFEX: pitch **1.0**, rate 0.95 (suara browser) atau XTTS bila `TTS_URL` diisi. Mikrofon dimatikan selama LAFEX bicara supaya tidak mendengar suaranya sendiri.
- Mikrofon belum diizinkan: pesan besar "Tekan Izinkan Mikrofon di atas" + satu tombol "Coba Lagi".
- `POST /api/lafex-chat/` `{pesan, mode, bahasa, topik}` -> `{jawaban, koreksi, benar, ...}` memakai `ai/llm.py` dengan jatah harian dan batas 8/menit yang sama dengan chat biasa.

## Pemetaan mode ke karakter AI
| Mode | Karakter | Tambahan perintah (ditulis di server) |
|---|---|---|
| PREMAN | AI Bandidu (`preman`) | gaul dan santai, tetap sopan |
| PINTAR | AI Respeitozu (`sopan`) | guru sabar: koreksi SATU per SATU, minta mengulang |
| PROFESSIONAL | AI Matenek (`profesional`) | formal, seperti latihan wawancara kerja |

`benar` = jawaban tanpa koreksi. Topik dibersihkan sebelum masuk ke prompt.

## Beranda
`HOME_LANGSUNG_BICARA` bawaan **0**: siswa melewati halaman Siswa dulu. Nilai 1 mengalihkan pelajar langsung ke `/video-call/` (tanpa memilih materi).

## Catatan jujur
- **"Satu klik" ada batasnya karena aturan browser.** Chrome/Android memperbolehkan mikrofon yang sudah pernah diizinkan menyala sendiri, tetapi suara LAFEX bisa diblokir bila halaman belum disentuh. Bila itu terjadi (terutama iPhone/Safari), muncul ajakan satu kali **"Tekan layar untuk mulai ko'alia"**, lalu semuanya otomatis. Itu satu-satunya cara agar suara tetap dibolehkan browser.
- **Ini bukan video**, melainkan pergantian gambar + animasi mulut.
- **Suara Tetun**: browser tidak punya suara dan pengenalan Tetun; dipakai pt-PT (hasil sering salah dengar). Solusi nyata: Whisper + TTS Tetun di server (lihat `MELATIH_SUARA.md`).
- **Pakai headset** agar mikrofon tidak menangkap suara speaker. iPhone Safari sering menghentikan pengenalan suara; Chrome/Edge Android paling baik. Butuh HTTPS.
- Poin hanya tampilan di browser (localStorage), bisa diubah pengguna.
- Diuji di Chromium dengan mikrofon/suara palsu dan PNG uji; belum diuji di HP sungguhan atau dengan gambar Anda.
