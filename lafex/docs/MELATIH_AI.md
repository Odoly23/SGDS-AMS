# Memakai AI gratis (Gemma dll) dan melatihnya lagi

Aplikasi sudah punya backend `local`: bicara ke server model open-source lewat API kompatibel OpenAI.
Tidak ada biaya per token; Anda hanya membayar/menyiapkan komputer (server/GPU) sendiri.

## 1. Jalankan model gratis (paling mudah: Ollama)
```bash
ollama pull gemma2:2b        # atau gemma2:9b bila RAM/GPU cukup
```
`.env`:
```
AI_BACKEND=local
LOCAL_LLM_URL=http://127.0.0.1:11434/v1
LOCAL_LLM_MODEL=gemma2:2b
```
Alternatif: `llama-server` (llama.cpp), vLLM, LM Studio, atau layanan dengan kuota gratis (Groq, OpenRouter) lewat `LOCAL_LLM_URL` + `LOCAL_LLM_KEY`.

## 2. Latih lagi (LoRA)
```bash
python manage.py export_finetune --out train.jsonl      # hanya kalimat berstatus "terverifikasi"
```
Latih dengan skrip LoRA (mis. `../timor_ai/training/finetune_lora.py` atau Unsloth/TRL di Colab/Kaggle gratis),
gabungkan adapter ke model, ubah ke GGUF, lalu daftarkan di Ollama (`ollama create lafex-gemma -f Modelfile`) dan set `LOCAL_LLM_MODEL=lafex-gemma`.

## Peringatan jujur
- Gemma 2B/9B **belum bisa Tetun dengan baik**, apalagi bahasa daerah (Mambae dll). Tanpa data bagus hasilnya akan banyak salah.
- Data latihan harus dicek **penutur asli** (status "terverifikasi"). Teks draf dari AI jangan dipakai melatih: kesalahan akan "terkunci" di model.
- Contoh yang dihasilkan perintah di atas masih sedikit dan berpola; untuk kualitas nyata dibutuhkan ribuan percakapan asli dari kontributor.
- Format jawaban harus JSON (`tet,en,koreksi,gerak`); model kecil kadang melanggarnya: aplikasi memakai parser toleran, tapi giliran gagal tidak dihitung.
- Suara (rekaman crowdsource) baru berguna bila ada model ucapan-ke-teks yang dilatih (mis. Whisper); itu proyek terpisah dari model teks.
- Belum diuji dengan server model sungguhan di lingkungan ini.
