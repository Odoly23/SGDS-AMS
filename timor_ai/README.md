# LAFEX-AI — Asisten AI untuk Timor-Leste

Chatbot + penerjemah multibahasa untuk Timor-Leste. **Bukan model dari nol**: kita pakai
model open-source kecil (**Gemma 2 2B/9B**), ditambah **LoRA** (belajar bahasa lokal) dan
**RAG** (jawaban berdasar dokumen lokal, bukan halusinasi).

> Status jujur: kerangka aplikasi, admin, RAG, seeder, dan evaluasi sudah **diuji jalan**
> (8 tes otomatis lulus, memakai SQLite + backend `dummy`). Yang **belum diuji di sini**:
> PostgreSQL asli, memuat Gemma sungguhan, `sentence-transformers`, dan training LoRA di GPU.
> Alurnya sudah disiapkan; uji dulu bertahap (lihat bagian 6).

---

## 1. Arsitektur (diagram teks)

```
 HP / Laptop (browser)
        │  Django Template + Tailwind (chat.html, JS fetch)
        ▼
 ┌──────────────────────── Django 5 + DRF ────────────────────────┐
 │  core/      settings, urls, login email + Facebook (allauth)   │
 │  chat/      API: /api/chat/  /api/detect/  /api/languages/ ...  │
 │             ├─ detect.py   auto-detect bahasa (Tetun manual +   │
 │             │              langdetect untuk pt/en/id)           │
 │             ├─ services.py logika mode CHAT dan TRANSLATE       │
 │             └─ llm.py      Gemma 2 (+ adapter LoRA)             │
 │  datasets/  Phrase + Translation (crowdsourcing, status draft→ │
 │             review→verified) ──► export JSONL untuk LoRA        │
 │  rag/       Document(PDF/TXT) → Chunk + embedding → search()    │
 └───────────────┬─────────────────────────────┬──────────────────┘
                 ▼                             ▼
           PostgreSQL                   training/finetune_lora.py
  (user, chat log, dataset, chunk)      (di Colab/Kaggle/GPU) → adapter LoRA
```

**Alur satu pertanyaan (mode Tanya Jawab):**
`pesan user → detect bahasa → rag.search() ambil 4 potongan dokumen terdekat → susun prompt
(aturan + KONTEKS + riwayat) → Gemma(+LoRA) → jawaban + daftar sumber → disimpan di Message`

**Alur mode Terjemahan:**
`teks → (1) cari kalimat SAMA PERSIS di tabel Translation (memori terjemahan, tanpa halusinasi)
→ (2) kalau tidak ada: ambil contoh mirip dari DB sebagai few-shot → LLM menerjemahkan →
peringatan "eksperimental" untuk bahasa lokal`

### Struktur folder
```
timor_ai/
├── manage.py
├── requirements.txt          # web + RAG
├── requirements-ai.txt       # torch/transformers/peft (berat)
├── .env.example
├── core/                     # settings.py, urls.py, context_processors.py
├── chat/                     # models, views, urls, serializers, services, llm, detect, prompts, admin
├── datasets/                 # models (Phrase, Translation, Vote), services, halaman /kontribusi/, admin, seed/
├── rag/                      # models, admin (upload PDF/TXT), services (chunk/embed/search)
├── billing/                  # poin prabayar, paket, voucher (ala pulsa), admin laporan
├── templates/                # base.html, chat/chat.html, account/{login,signup}.html
├── training/finetune_lora.py # LoRA
└── evaluation/eval_language.py
```

---

## 2. Koreksi daftar bahasa (WAJIB dibaca)

Daftar awal Anda tertulis "30 bahasa lokal", tetapi isinya 32 nama dengan 3 duplikat, dan
literatur umumnya menyebut sekitar **16–19** bahasa asli Timor-Leste. Semua catatan ada di
`chat/language_registry.py` dan tampil di Admin > Bahasa (kolom "Perlu diverifikasi").

| Daftar awal | Perbaikan | Catatan |
|---|---|---|
| Tetum | **Tetun** | Ejaan resmi dalam bahasanya sendiri adalah *Tetun* |
| Tetum Terik | **Tetun Terik** | Ini *varian* Tetun, bukan bahasa terpisah |
| Mambae (2×) | **Mambae** | Duplikat digabung |
| Idalaka + Idate | **Idaté** | Duplikat digabung ("Idalaka" = nama kelompok etnis) |
| Dadua + Dadu'a | **Dadu'a** | Duplikat digabung |
| Baikeno (Uab Meto) | **Baikenu** | Ejaan umum |
| Galoli | **Galolen** | |
| Habun | **Habu** | |
| Makuva | **Maku'a (Lóvaia)** | |
| Kairui, Midiki | tetap, **tapi** | Sering dianggap satu bahasa "Kairui-Midiki" — tentukan dipisah/digabung |
| Atauru, Bekais, Isni, Lolein, Nanaek, Rahesuk, Raklungu, Resuk, Sa'ane, Welaun | ditandai **"verify"** | **Saya tidak bisa memastikan** semuanya bahasa tersendiri; sebagian mungkin dialek/nama desa (beberapa tampaknya terkait Pulau Atauro). Cek ke **INL-UNTL** (Instituto Nacional de Linguística) / Glottolog sebelum dipakai resmi |

Bahasa "verify" tetap ada di database (tidak dibuang), hanya diberi tanda (?) di menu.

---

## 3. Cara menjalankan

### Prasyarat
Python 3.10+ dan PostgreSQL 14+ (atau pakai SQLite dulu untuk coba cepat).

### Linux Mint
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip postgresql
sudo -u postgres psql -c "CREATE DATABASE lafex_ai;"
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"

cd SGDS-AMS/timor_ai
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # lalu edit isinya
```
### Windows (PowerShell)
```powershell
# Install Python & PostgreSQL dulu (python.org, postgresql.org), buat database "lafex_ai" lewat pgAdmin
cd SGDS-AMS\timor_ai
py -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # lalu edit isinya
```
> Mau coba tanpa PostgreSQL? Di `.env` isi `DB_ENGINE=sqlite`.

### Langkah yang sama di Linux & Windows
```bash
python manage.py migrate                 # buat tabel
python manage.py seed_phrases            # isi 33 bahasa + 100 kalimat x 3 bahasa
python manage.py setup_groups            # grup Kontributor & Reviewer
python manage.py createsuperuser         # akun admin (login admin di /admin/)
python manage.py runserver
```
Buka http://127.0.0.1:8000/ (chat) dan http://127.0.0.1:8000/admin/ (admin).
Karena `LLM_BACKEND=dummy`, jawaban masih berupa "mode demo" — itu normal; alurnya sudah bisa dicoba
(termasuk terjemahan dari database dan pencarian RAG).

Tes otomatis: `python manage.py test` · Evaluasi bahasa: `python evaluation/eval_language.py`

---

## 4. Endpoint API (butuh login)

| Method | URL | Fungsi |
|---|---|---|
| GET | `/api/languages/` | daftar bahasa aktif |
| POST | `/api/chat/` | kirim pesan |
| POST | `/api/detect/` | `{"text": "..."}` → bahasa terdeteksi |
| GET | `/api/conversations/` | riwayat milik user |
| GET/DELETE | `/api/conversations/<id>/` | isi / hapus percakapan |
| GET | `/api/wallet/` | saldo poin + daftar paket |
| POST | `/api/redeem/` | `{"code": "ABCD-EFGH-JKLM"}` tukar voucher jadi poin |

Kode error `/api/chat/`: **402** poin habis, **429** terlalu cepat, **503** model gagal (user tidak ditagih).

```json
// Tanya jawab
{"message": "Tais ne'e saida?", "language": "tet", "mode": "chat"}
// Terjemahan Indonesia -> Portugis
{"message": "Selamat pagi", "language": "por", "mode": "translate", "source_language": "ind"}
```

---

## 5. Mengaktifkan model AI

Ada dua jalur. **Jalur A (bagian 5A): model berbayar lewat API**, Anda bayar per token, tanpa GPU, cocok untuk berjualan. **Jalur B: Gemma 2 lokal**, gratis per token tapi butuh RAM/GPU dan lebih lemah. Keduanya memakai kode yang sama; pilih lewat `LLM_BACKEND` di `.env`.

### 5A. Model berbayar lewat API (`LLM_BACKEND=anthropic`)
1. Buat akun di console.anthropic.com, isi saldo, buat **API key**, dan **atur batas pengeluaran bulanan** di Console (pengaman paling penting).
2. `.env`: `LLM_BACKEND=anthropic`, `ANTHROPIC_API_KEY=...`, `ANTHROPIC_MODEL=...`, lalu isi `PRICE_IN_PER_M` / `PRICE_OUT_PER_M` sesuai model itu.
3. Kunci hanya ada di server; browser user tidak pernah melihatnya. Jangan commit `.env`.

| Model (`ANTHROPIC_MODEL`) | Harga per 1 juta token (masuk / keluar) | Catatan |
|---|---|---|
| `claude-opus-5-5` (default) | $4 / $20 | paling pintar, paling mahal |
| `claude-sonnet-5-5` | $2 / $10 | menengah |
| `claude-haiku-5-5` | $0,10 / $0,50 | jauh lebih murah, kualitas lebih sederhana |

Harga di atas dari daftar yang saya miliki per awal November 2026; **cek halaman harga resmi sebelum menetapkan harga jual**. Memilih model adalah keputusan Anda; uji kualitas Tetun/Portugis dengan `evaluation/eval_language.py` pada tiap model.

### 5B. Gemma 2 2B lokal (langkah demi langkah)

**A. Akun & token Hugging Face (sekali saja, harus Anda lakukan sendiri)**
1. Daftar di https://huggingface.co lalu login.
2. Buka https://huggingface.co/google/gemma-2-2b-it → klik **Acknowledge license** (Gemma modelnya "gated"; tanpa ini unduhan ditolak).
3. Buat token tipe **Read** di https://huggingface.co/settings/tokens. Simpan; jangan dibagikan atau di-commit.

**B. Pasang paket AI** (di dalam venv). Pasang torch dulu:
```bash
# Tanpa GPU (Linux Mint / Windows):
pip install torch --index-url https://download.pytorch.org/whl/cpu
# Punya GPU NVIDIA: ikuti perintah di https://pytorch.org/get-started/locally/
pip install -r requirements-ai.txt
```

**C. Edit `.env`**
```
LLM_BACKEND=hf
HF_TOKEN=hf_xxxxxxxxxxxxxxxx
LLM_DTYPE=bfloat16
EMBEDDING_BACKEND=sentence-transformers
```
Lalu indeks ulang dokumen RAG (vektor lama dari `hash` tidak cocok): `python manage.py reindex_rag`

**D. Periksa kesiapan** — perintah ini memeriksa token, lisensi, RAM/GPU, lalu mencoba satu jawaban:
```bash
python manage.py check_llm --skip-generate   # cek cepat, tanpa unduh model
python manage.py check_llm                   # + unduh model (~5 GB) dan tes jawab
```
Setiap `[GAGAL]` disertai petunjuk perbaikannya. Setelah lolos: `python manage.py runserver` dan coba chat.

**Kebutuhan kasar & ekspektasi**
- **2B (bfloat16):** RAM bebas ≥ 6 GB di CPU (lambat, ±beberapa detik per kata) atau GPU ≥ 6 GB. Jika CPU Anda lama dan error/sangat lambat, coba `LLM_DTYPE=float32` (butuh ±11 GB RAM).
- Unduhan pertama ±5 GB, tersimpan di cache Hugging Face untuk seterusnya.
- **9B:** ganti `LLM_MODEL_ID=google/gemma-2-9b-it`; butuh GPU ≥ 24 GB atau kuantisasi 4-bit.
- Tetun & bahasa lokal masih lemah sebelum LoRA (bagian di bawah) — itu wajar.

**Masalah umum**
| Pesan | Penyebab / solusi |
|---|---|
| `GatedRepoError` / 401 / 403 | Lisensi belum di-acknowledge atau token salah (langkah A) |
| `MemoryError` / proses "Killed" | RAM kurang → tutup aplikasi lain, atau pakai GPU / model lebih kecil |
| Sangat lambat | Normal di CPU; kurangi `LLM_MAX_NEW_TOKENS` (mis. 150) |
| Chat pertama lama | Model dimuat saat permintaan pertama (hanya sekali per proses server) |

### LoRA (belajar bahasa lokal)
```bash
python manage.py export_finetune --out training/train.jsonl     # hanya data "verified"
python training/finetune_lora.py --data training/train.jsonl --max-steps 20   # uji cepat dulu
# lalu .env: LLM_LORA_PATH=training/output/lora-gemma2-2b
```
Latih di Google Colab / Kaggle (GPU gratis) lalu unduh folder adapter-nya (puluhan MB).
Untuk uji pipeline saja boleh `--include-draft`, **jangan** untuk model sungguhan.

### Upgrade ke pgvector / FAISS (kalau data besar)
Sekarang vektor disimpan sebagai JSON dan dihitung dengan numpy: sederhana, jalan di PostgreSQL biasa,
cukup untuk ±puluhan ribu potongan. Jika lebih besar: `pip install pgvector`, ganti `Chunk.embedding` ke
`pgvector.django.VectorField(dimensions=384)` + migrasi `VectorExtension()`, dan ganti `rag.services.search()`
dengan `Chunk.objects.order_by(CosineDistance("embedding", q))[:k]`. Interface `search()` tidak berubah.

---

## 6. Batasan & hal yang perlu Anda tahu

1. **Data bahasa lokal sangat sedikit.** Gemma tidak pernah dilatih Mambae/Makasae dan semacamnya; Tetun pun
   terbatas. LoRA dengan beberapa ratus kalimat hanya mengajarkan *pola dasar*, bukan kefasihan. Targetkan
   dulu: sapaan, kosakata, kalimat pendek. Jangan klaim "AI fasih bahasa X" sebelum dinilai penutur asli.
2. **Seed data = draft.** Tetun/Portugis/Inggris di `seed_data.json` ditulis AI dan **harus dicek penutur asli**
   (status `draft`). **Mambae & Makasae sengaja kosong** — saya tidak mau mengarang bahasa daerah. Seeder
   baru memuat 3 bahasa terisi; 100 kalimat itu adalah *kerangka* yang siap diisi komunitas.
3. **Auto-detect** hanya untuk Tetun (heuristik kata), Portugis, Inggris, Indonesia. Bahasa lokal dipilih manual.
   Teks pendek / campur-kode (Tetun + Portugis) sering salah.
4. **Embedding** `multilingual-e5-small` bagus untuk Portugis/Inggris/Indonesia, lemah untuk Tetun; dokumen
   RAG sebaiknya Portugis/Indonesia/Inggris/Tetun yang baku. `EMBEDDING_BACKEND=hash` hanya untuk tes.
5. **PDF hasil scan** (gambar) tidak terbaca → butuh OCR (mis. `ocrmypdf`) dulu.
6. **Hak cipta & adat (lulik):** isi kolom "Sumber/lisensi" tiap dokumen. Cerita adat/lisan tertentu bisa
   bersifat sakral atau milik komunitas — minta izin tetua/komunitas sebelum dimasukkan.
7. Untuk **hukum & kesehatan**, AI hanya memberi informasi umum; pasang disclaimer di produksi.
8. Produksi: `DJANGO_DEBUG=0`, `SECRET_KEY` unik, HTTPS, gunakan gunicorn + nginx, dan build Tailwind
   (sekarang pakai CDN agar simpel). Batasi laju (rate limit) API agar server murah tidak kewalahan.

---

## 7. Crowdsourcing data bahasa lewat Django Admin

**Prinsip:** jangan percaya satu orang; setiap kalimat melewati *draft → review → verified*.
Hanya `verified` masuk training (`export_finetune`).

**Peran** (jalankan `python manage.py setup_groups`, lalu Admin > Users > centang *Staff status* + pilih grup):
- **Kontributor** (guru, mahasiswa UNTL, tokoh masyarakat): menambah Terjemahan; status otomatis *draft*.
- **Reviewer** (penutur asli / ahli bahasa, mis. dari INL): bisa tindakan **"Tandai terverifikasi"**/"Tolak", dan upload dokumen RAG.

**Cara kerja di lapangan:**
1. Admin > *Kalimat (konsep)* > buka satu kalimat > di bagian bawah isi terjemahan per bahasa (inline). Catat **dialek/daerah** — Mambae Ainaro ≠ Mambae Same.
2. Untuk volume besar: ekspor `seed_phrases.csv`, bagikan lewat Excel/Google Sheet/WhatsApp ke relawan
   (kolom `mambae`, `makasae` kosong), kumpulkan lagi, lalu impor:
   `python manage.py seed_phrases --file hasil.csv --source "relawan-Baucau"` (masuk sebagai *draft*).
3. Reviewer memfilter Translation *status = Menunggu review*, bahasa tertentu, lalu verifikasi massal.
4. Kolom **Sumber** dan **Catatan** menjaga jejak asal data; **Export CSV** tersedia di Admin untuk audit.
5. Tambahkan kalimat baru kapan saja (Admin > Kalimat > Tambah), kategori mis. *adat*, *hukum*.

**Tips agar data terkumpul:** kerja sama dengan UNTL/INL, sekolah, gereja/paroki, radio komunitas;
mulai dari *satu* bahasa dulu (mis. Mambae atau Makasae, penutur terbanyak); beri target mingguan
(mis. 50 kalimat terverifikasi/minggu) dan tampilkan progres lewat filter Admin. Rekaman audio & cerita lisan
dapat ditranskripsi lalu diunggah sebagai Dokumen RAG (dengan izin).

---

## 8. Langkah berikutnya (saran urutan)
1. Jalankan dengan `dummy` → pastikan admin, seeder, chat jalan.
2. Unggah 3–5 dokumen kecil (sejarah, budaya) → uji RAG dengan `EMBEDDING_BACKEND=sentence-transformers`.
3. Aktifkan Gemma 2 2B (`hf`) → jalankan `evaluation/eval_language.py`.
4. Kumpulkan data komunitas → verifikasi → LoRA → bandingkan skor evaluasi sebelum/sesudah.


---

## 9. Berjualan seperti pulsa (poin prabayar)

**Konsep:** user membeli *paket* → mendapat **poin** → tiap jawaban AI memotong poin sesuai token yang benar-benar terpakai. Poin habis = tidak bisa chat sampai isi ulang. Terjemahan yang diambil dari basis data (tanpa memanggil model) **gratis**.

```
biaya_poin = ceil( (token_masuk x harga_in + token_keluar x harga_out) / 1.000.000 x MARGIN x POINTS_PER_USD )
```
Semua angka di `.env` (`PRICE_*`, `BILLING_MARGIN`, `POINTS_PER_USD`).

**Perkiraan biaya** (satu tanya jawab RAG ≈ 1.500 token masuk + 300 keluar, belum termasuk token "berpikir" model; ukur sendiri lewat Admin > Transaksi poin):

| Model | Biaya Anda / jawaban | Poin dipotong (margin 3x, 1.000 poin = $1) | Jawaban per paket $1 |
|---|---|---|---|
| Opus 5.5 | ≈ $0,012 | ≈ 36 | ≈ 27 |
| Sonnet 5.5 | ≈ $0,006 | ≈ 18 | ≈ 55 |
| Haiku 5.5 | ≈ $0,0003 | 1 (batas minimum) | ≈ 1.000 |

Selisihnya sangat besar, jadi **pilihan model menentukan harga paket Anda**. Poin gratis untuk user baru (`TRIAL_CREDITS`, default 100) adalah **biaya dari kantong Anda**; kecilkan jika Anda memakai model mahal.

**Alur penjualan:**
1. Admin > Paket: buat paket (mis. "Paket $1 = 1.000 poin", "Paket $5 = 6.000 poin").
2. Cetak voucher: `python manage.py make_vouchers --package 1 --count 50 --batch kios-dili --out voucher.csv` (opsi `--days 90` untuk masa berlaku).
3. Jual kode lewat agen/kios/WhatsApp. User memasukkan kode di kolom "Kode voucher" di menu samping.
4. Kode hanya tampil sekali di CSV; database menyimpan hash-nya. Voucher sekali pakai; salah ketik 5x = terkunci 15 menit.
5. Admin > Transaksi poin: laporan pemakaian + Export CSV. Admin > Dompet: tambah poin manual (mis. kompensasi).

**Soal "seperti pulsa Telkomsel":** kode voucher di atas meniru pengalaman pulsa (beli kartu/kode, masukkan, saldo bertambah) dan **sudah jalan**. Menagih langsung dari pulsa operator (*carrier billing*) **belum ada** di kode ini: itu butuh kontrak dengan operator atau agregator dan API-nya. Setahu saya anak usaha Telkomsel di Timor-Leste bernama **Telkomcel**; tanyakan langsung ke mereka tentang reseller atau carrier billing. Sampai ada, pembayaran bisa lewat agen yang menerima tunai/transfer lalu menjual voucher. Saya tidak tahu skema resmi Telkomcel; jangan menulis "bayar pakai pulsa Telkomcel" di promosi sebelum ada perjanjian tertulis.

**Pengaman biaya Anda:** (1) batas pengeluaran di Console API; (2) saldo minimum `MIN_BALANCE_TO_CHAT`; (3) batas `MAX_MESSAGES_PER_MINUTE` per user; (4) verifikasi email wajib sebelum dapat poin gratis; (5) panggilan model yang gagal tidak menagih user. Untuk produksi dengan banyak proses (gunicorn), ganti cache bawaan (memori per proses) dengan Redis agar batas kecepatan dan kunci voucher berlaku untuk semua proses.

---

## 10. Login: email dan Facebook

Memakai **django-allauth**. User bisa daftar dengan **email + password** (wajib klik tautan verifikasi di email) atau **Facebook saja** (tanpa password). Jika akun Facebook tidak memberi email, user diminta mengisinya.

**Email:** isi `EMAIL_HOST`, `EMAIL_HOST_USER`, dst. di `.env` (SMTP, mis. dari penyedia email Anda). Tanpa itu, email verifikasi tampil di terminal (cukup untuk belajar). Untuk uji lokal cepat: `ACCOUNT_EMAIL_VERIFICATION=optional`.

**Facebook (dilakukan sekali di developers.facebook.com):**
1. Buat App baru dengan fitur **Facebook Login**.
2. Settings > Basic: salin **App ID** dan **App Secret** ke `.env` (`FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`). Tombol Facebook baru muncul jika keduanya terisi.
3. Facebook Login > Settings > **Valid OAuth Redirect URIs**: `https://domain-anda/accounts/facebook/login/callback/` (lokal: `http://localhost:8000/accounts/facebook/login/callback/`).
4. Admin Django > **Sites**: ubah `example.com` menjadi domain Anda.
5. Selama app berstatus *Development*, hanya admin/penguji app yang bisa login. Agar umum bisa login, app harus *Live*, dan Meta mewajibkan **URL kebijakan privasi** dan petunjuk **penghapusan data**. Syarat Meta bisa berubah; cek dokumen Facebook Login terbaru.

**Kebijakan privasi (wajib ditulis sebelum buka untuk umum):** pesan user dikirim ke penyedia model (jalur 5A) agar dijawab; sebutkan itu. Kode hanya mengirim isi percakapan dan konteks dokumen, bukan email/nama user.

**Yang sudah diuji / belum:** halaman login & daftar, kewajiban verifikasi email, dan tombol Facebook (muncul hanya jika dikonfigurasi) sudah diuji otomatis. **Alur OAuth Facebook sungguhan belum diuji** (butuh app Facebook Anda). Panggilan ke API model diuji dengan klien palsu; **belum pernah dipanggil dengan kunci asli** dari lingkungan pengembangan.

---

## 11. Bahasa daerah (Mambae, dll.) dan Inggris di model berbayar

Pilihan bahasa jawaban (Tetun, Portugis, Inggris, Indonesia, atau bahasa daerah) dikirim ke model lewat instruksi sistem. **Inggris, Portugis, Indonesia** berjalan baik di model besar. **Tetun** cukup baik tetapi perlu dicek penutur asli. **Mambae dan bahasa daerah lain**: model besar pun belum pernah dilatih dengan data memadai, jadi ia bisa salah atau mengarang. Itu sebabnya aplikasi (1) memberi peringatan eksperimental, (2) memakai **contoh terverifikasi dari komunitas** sebagai petunjuk di prompt, dan (3) mengutamakan **memori terjemahan** untuk kalimat yang sudah ada. Kualitas Mambae akan naik sebanding dengan jumlah kalimat terverifikasi (bagian 7), bukan dengan model yang lebih mahal.


---

## 12. Model dari nol, atau crowdsourcing? (jawaban lengkap)

**Melatih model bicara dari nol tidak realistis untuk Mambae/Makasae dkk.**
- Model bahasa belajar dari **miliaran sampai triliunan kata**. Gemma 2 2B dilatih dengan sekitar 2 triliun token. Untuk Mambae, data tertulis yang ada mungkin hanya ribuan kalimat (angka ini perkiraan saya, bukan hasil pengukuran). Model yang dilatih dari nol dengan data sebanyak itu akan menghasilkan teks acak.
- Biaya komputasi kasar untuk satu model 2B dari nol: puluhan ribu jam GPU kelas A100, ratusan ribu dolar. Itu pun hanya jika datanya ada.
- Jadi yang menentukan bukan "model dari nol atau tidak", melainkan **berapa banyak kalimat terverifikasi yang berhasil dikumpulkan**. Data itulah yang dipakai di semua jalur: contoh di prompt, memori terjemahan, LoRA, atau nanti model terjemahan khusus.

**Jalur bertahap yang masuk akal** (setiap tahap memakai data dari tahap sebelumnya):
| Jumlah kalimat terverifikasi per bahasa | Yang bisa dilakukan |
|---|---|
| 0 - 500 | Memori terjemahan + contoh di prompt (sudah ada). Cukup untuk sapaan dan frasa dasar. |
| 500 - 5.000 | LoRA pada Gemma (`export_finetune`), atau fine-tune model terjemahan yang sudah ada untuk bahasa mirip. Pola kalimat sederhana mulai benar. |
| 5.000+ | Model terjemahan khusus per bahasa; evaluasi resmi dengan penutur asli. Suara (pengenalan/pembuatan ucapan) adalah proyek terpisah yang butuh rekaman audio, bukan hanya teks. |

Batas angka di tabel adalah patokan kasar untuk perencanaan, bukan jaminan kualitas.

### Halaman crowdsourcing untuk user: `/kontribusi/`
Sudah ada di aplikasi (tautan "Bantu bahasa daerah" di menu samping chat). Tiga tab:
1. **Terjemahkan:** user memilih bahasa yang dikuasai, lalu melihat kalimat dalam Tetun/Indonesia/Portugis/Inggris dan menulis terjemahannya (+ dialek, mis. Ainaro). Kalimat yang belum punya terjemahan di bahasa itu didahulukan.
2. **Periksa:** user melihat terjemahan orang lain dan menekan *Benar* / *Salah*. Draf buatan AI dari seeder juga diperiksa di sini.
3. **Papan skor:** peringkat berdasarkan jumlah terjemahan terverifikasi, memakai nama samaran ("Kontributor #12"), email tidak ditampilkan.

**Jaminan kualitas (penting):**
- Kiriman user berstatus *draft* dan **tidak dipakai untuk apa pun** sampai diverifikasi.
- 3 suara *Benar* hanya mendorong terjemahan ke **antrean reviewer**. Suara komunitas tidak pernah memverifikasi sendiri, jadi akun palsu tidak bisa mengisi data sampah ke model.
- **Reviewer** (penutur asli/ahli, grup "Reviewer") memutuskan di Admin > Terjemahan. Kolom *Suara* menunjukkan setuju/tidak, filter status *Menunggu review*, aksi *Tandai terverifikasi* / *Tolak*.
- Batas harian: 40 kiriman dan 100 pemeriksaan per user (`CONTRIB_MAX_*` di `.env`). Terjemahan ganda ditolak. User tidak bisa memeriksa tulisan sendiri.
- Pengisi menyatakan sendiri bahasa yang dikuasai, **tidak ada pembuktian**. Itulah gunanya langkah reviewer.

**Hadiah poin (mengikat ke sistem poin):**
| Kejadian | Hadiah |
|---|---|
| Terjemahan Anda **terverifikasi** reviewer | +50 poin (`CONTRIB_REWARD_VERIFIED`) |
| Anda memilih *Benar* dan terjemahan itu akhirnya terverifikasi | +2 poin (`CONTRIB_REWARD_VOTE`) |
Hadiah dibayar sekali per terjemahan dan hanya setelah reviewer manusia memverifikasi. Reviewer tidak mendapat hadiah dari verifikasi tulisannya sendiri. Hadiah adalah biaya Anda: 50 poin setara kira-kira 1-2 jawaban jika memakai model mahal, atau puluhan jawaban jika memakai model murah (bagian 9). Sesuaikan angkanya.

**Cara memulai di lapangan:**
1. `python manage.py setup_groups`, lalu jadikan 2-3 orang yang Anda percaya (guru bahasa, dosen UNTL, tokoh komunitas) sebagai **Reviewer** (Admin > Users: centang *Staff status* + grup Reviewer).
2. Mulai dari **satu bahasa** (mis. Mambae atau Makasae, penutur terbanyak) dan 100 kalimat seed. Target mingguan, mis. 50 kalimat terverifikasi.
3. Undang kontributor lewat sekolah, paroki, radio komunitas, grup WhatsApp/Facebook. Kontributor tidak perlu staf Admin; cukup daftar akun biasa.
4. Pantau Admin > Terjemahan (filter bahasa/status) dan laporan poin di Admin > Transaksi poin (jenis *Hadiah kontribusi*).
5. Bila 500+ kalimat terverifikasi: `export_finetune` lalu latih LoRA (bagian 5B) dan bandingkan skor sebelum/sesudah.

**Belum ada:** rekaman suara/audio, pembuktian identitas penutur, notifikasi ke reviewer, dan penambahan kalimat baru oleh user biasa (kalimat baru ditambah admin lewat Admin > Kalimat atau impor CSV). Saya bisa menambahkannya bertahap.
