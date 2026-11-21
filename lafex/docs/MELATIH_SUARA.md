# Whisper dan XTTS untuk Tetun: yang sudah siap dan yang masih harus Anda kerjakan

## Kenyataan dulu (baca ini)
- **Whisper bawaan tidak punya Tetun**, dan **XTTS-v2 bawaan tidak punya Tetun**. Tanpa fine-tune, keduanya hanya "mendekati" lewat Portugis/Indonesia.
- Untuk hasil yang layak, bahasa baru butuh **puluhan jam** audio bertranskripsi dari **banyak penutur**. Belasan menit hanya untuk menguji alur.
- **Lisensi XTTS-v2 (Coqui Public Model License) hanya untuk NON-KOMERSIAL.** Anda menjual paket/pulsa ke pengguna: itu komersial, jadi XTTS-v2 **tidak boleh** dipakai begitu saja. Cek lisensi sebelum meluncur. Alternatif yang lisensinya longgar: **Piper** (MIT), atau model lain yang lisensinya membolehkan komersial. (Meta MMS punya Tetum, tapi bobotnya CC-BY-NC: juga non-komersial; saya belum memverifikasi isi lengkapnya.) Whisper (MIT) boleh komersial.
- Saya **tidak bisa melatih atau menjalankan model di lingkungan ini** (tidak ada GPU). Yang disiapkan adalah sambungan aplikasi, halaman admin/kontributor, dan jalur data. Semuanya diuji dengan server palsu, belum dengan Whisper/XTTS sungguhan.

## Yang sudah ada di aplikasi
| Bagian | Fungsi |
|---|---|
| `ai/suara.py` | Klien Whisper (`STT_URL`, API kompatibel OpenAI `/audio/transcriptions`) dan XTTS (`TTS_URL`, JSON `{text, speaker_wav, language}`). Mati bila URL kosong. |
| Admin: `/crowdsource/tinjau/` | Tombol **Whisper (draf)** per rekaman dan **Whisper untuk semua yang menunggu** (maks. 15 sekali jalan). Hasilnya berlabel *Draf Whisper* dan tidak boleh menimpa yang sudah diperiksa admin. |
| Admin: `/ai/suara/` | Status server Whisper/XTTS, jumlah menit data latihan siap pakai per bahasa, perintah ekspor. |
| Kontributor: `/crowdsource/kontribusiku/` | Kontributor menulis sendiri apa yang ia ucapkan (opsional). Terkunci setelah admin memeriksa. |
| Kontributor: halaman rekam | Tombol **Rona ezemplu**: XTTS bila dipasang, jika tidak suara browser. |
| `/ai/tts/` dan Video Call | Jawaban Tetun diputar dengan XTTS bila `TTS_URL` diisi; jika server mati/lambat otomatis kembali ke suara browser. Kalimat yang sama di-cache, batas 20 permintaan/menit/user. |
| `python manage.py export_suara` | Menulis data latihan: `whisper/train.jsonl` + wav 16 kHz dan `xtts/metadata.csv` (`audio_file|text|speaker_name`) + wav 22,05 kHz. |

**Aturan kualitas data:** hanya rekaman berstatus *disetujui* dengan transkripsi dari **kontributor atau admin** yang diekspor. **Draf Whisper tidak pernah diekspor** (kalau tidak, model belajar dari kesalahannya sendiri). Berkas ekspor tidak memuat kode pengirim/nama; nama berkas hanya nomor rekaman.

## Langkah kerja
1. Kontributor merekam kalimat dan (opsional) menulis ucapannya. Admin menyetujui di **Tinjau**, memakai **Whisper (draf)** untuk mempercepat, lalu **memperbaiki dan menyimpan** transkripsi (itu menandainya "diperiksa admin").
2. Pantau menit data di **/ai/suara/**. Satu bahasa per model.
3. `python manage.py export_suara --out data_suara --bahasa fataluku` (butuh `ffmpeg`).
4. **Whisper**: pakai `training/finetune_whisper.py` (atau buka `training/whisper_colab.ipynb` di Colab/Kaggle, GPU T4 gratis cukup untuk `whisper-small`; `--lora` untuk `medium`):
   ```bash
   pip install -U transformers accelerate soundfile peft
   python training/finetune_whisper.py --data data_suara/whisper --out hasil/whisper-tet --model openai/whisper-small --epochs 8 --baseline
   ```
   Skrip membagi data latih/dev **berdasarkan isi kalimat** (kalimat yang sama dari beberapa penutur tidak bocor ke dev), menghitung WER, menolak jalan bila data < 200 rekaman (kecuali `--paksa`), dan mencetak perintah konversi untuk faster-whisper. Sajikan hasilnya dengan faster-whisper-server atau whisper.cpp, lalu `.env`: `STT_URL=http://server:8000/v1` dan `STT_MODEL=<nama model Anda>`.
   - **Apa yang sudah diuji:** logika data/WER/pembagian (tes otomatis di `training/test_finetune_whisper.py`) dan seluruh alur latih (penuh dan `--lora`, simpan, muat ulang) dengan model Whisper mini ACAK di CPU (`training/bangun_model_uji.py`, tanpa unduhan). Satu bug versi library tertangkap di sini (argumen `warmup_ratio` dihapus di transformers terbaru) dan sudah diperbaiki.
   - **Yang belum:** belum dijalankan dengan model Whisper asli di GPU, jadi kecepatan, memori, dan angka WER sebenarnya belum diketahui. Jalankan `--max-steps 20` dulu.
   - **Token bahasa:** Whisper tidak punya token Tetun; bawaannya `--bahasa-token portuguese` (terdekat). Bisa diganti `indonesian` atau `tanpa` dan dibandingkan WER-nya.
   - **WER dev tetap optimistis:** nama penutur sengaja tidak disimpan (privasi), jadi penutur yang sama bisa ada di latih dan dev.
5. **TTS**: bila memakai XTTS (hanya untuk uji/non-komersial) latih dengan resep Coqui (`train_gpt_xtts.py`) pada `xtts/metadata.csv`; sajikan dengan xtts-api-server dan isi `TTS_URL`, `TTS_SUARA`, `TTS_BAHASA`. Untuk komersial pilih mesin berlisensi longgar (mis. Piper) dan sesuaikan `ai/suara.py:sintesis()` ke format API-nya.
6. Perintah/nama paket di langkah 4-5 adalah arah umum; ikuti dokumentasi terbaru tiap proyek, karena belum saya jalankan.

## Yang belum dikerjakan
- **Pengenalan suara sisi server di Video Call.** Panggilan masih memakai pengenalan suara browser (Tetun diperkirakan dengan pt-PT). Mengganti ke Whisper berarti browser merekam potongan audio (deteksi jeda) lalu mengirimnya ke server: bisa ditambahkan setelah ada model Tetun yang layak.
- **Penilaian kualitas otomatis** (mis. membandingkan Whisper dengan transkripsi manusia untuk menghitung WER). Belum ada.
