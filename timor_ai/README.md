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
 │  core/      settings, urls, signup/login (Django Auth)         │
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
├── core/                     # settings.py, urls.py, views.py (signup)
├── chat/                     # models, views, urls, serializers, services, llm, detect, prompts, admin
├── datasets/                 # models, admin (crowdsourcing), management/commands, seed/
├── rag/                      # models, admin (upload PDF/TXT), services (chunk/embed/search)
├── templates/                # base.html, chat/chat.html, registration/{login,signup}.html
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
python manage.py createsuperuser         # akun admin
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

```json
// Tanya jawab
{"message": "Tais ne'e saida?", "language": "tet", "mode": "chat"}
// Terjemahan Indonesia -> Portugis
{"message": "Selamat pagi", "language": "por", "mode": "translate", "source_language": "ind"}
```

---

## 5. Mengaktifkan Gemma 2 2B (langkah demi langkah)

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
