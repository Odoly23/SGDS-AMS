# Halaman Video Call LAFEX: cara pasang

File halaman: `ai/templates/ai/video_call.html` (satu file, HTML+CSS+JS tanpa pustaka).
Gambar yang dipakai (di folder static Anda): `static/img/lafex/{preman,pintar,pro}_{diam,ngomong,jempol,mikir}.png`.

## Link dari halaman Siswa
```html
<a href="/video-call/?mode=preman&bahasa=tetun&topik=perkenalan">Bicara dengan LAFEX</a>
```
`mode`: `preman` | `pintar` | `professional` (atau `pro`). `bahasa`: `tetun` | `portugues` | `inggris` | `indonesia`. `topik`: teks bebas pendek.
Tombol Kembali/Tutup memakai `history.back()` bila datang dari halaman yang sama; kalau tidak, menuju `URL_SISWA` (ubah di bagian PENGATURAN skrip).

## urls.py
```python
from django.urls import path
from . import views

urlpatterns = [
	path('video-call/', views.video_call, name='video-call'),
	path('api/lafex-chat/', views.lafex_chat, name='lafex-chat'),
]
```

## views.py
```python
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

MODE_OK = ('preman', 'pintar', 'professional')
BAHASA_OK = ('tetun', 'portugues', 'inggris', 'indonesia')

# Persona per mode: dipakai sebagai "system prompt" saat model sungguhan dipasang.
PERSONA = {
	'preman': "Kamu LAFEX, buaya kecil yang gaul dan santai. Pakai slang Tetun ringan ('Yo!', 'de'it', 'mai'). "
	          "Kalimat pendek, ramah, tidak kasar. Betulkan kesalahan dengan bercanda.",
	'pintar': "Kamu LAFEX, guru bahasa yang sabar. Betulkan tata bahasa SATU per SATU, jelaskan singkat, "
	          "beri contoh benar, lalu minta siswa mengulang. Nada hangat dan tenang.",
	'professional': "Kamu LAFEX, mitra latihan wawancara kerja. Gunakan bahasa formal (Portugis/Inggris formal "
	                "bila siswa memintanya). Sopan, jelas, beri umpan balik ringkas.",
}

# Jawaban tiruan (TANPA model) supaya halaman bisa dicoba sekarang.
MOCK = {
	'preman': "Yo! Diak, ita koalia ona! Koko dehan fali: 'Ha'u nia naran ...'",
	'pintar': "Diak liu! Ita nia fraze besik loos. Mai ita hatete fali ho calma.",
	'professional': "Muito bem. Pode apresentar-se, por favor? Diga o seu nome e a sua profissão.",
}
# Kata kunci jawaban yang dianggap BENAR untuk topik tertentu (tiruan; ganti dengan penilaian model).
KUNCI_BENAR = {'perkenalan': ('naran', 'nama', 'name', 'nome', "ha'u", 'hau', 'saya', 'my')}


@login_required
@ensure_csrf_cookie            # supaya cookie csrftoken ada untuk fetch POST di halaman
def video_call(request):
	# Halaman standalone (tanpa extends). Pakai render biasa; tidak ada tag Django di dalam file.
	return render(request, 'ai/video_call.html')


@login_required
@require_POST
def lafex_chat(request):
	try:
		data = json.loads(request.body.decode('utf-8'))
	except (ValueError, UnicodeDecodeError):
		return JsonResponse({'detail': 'JSON salah'}, status=400)
	pesan = str(data.get('pesan', '')).strip()[:500]
	mode = data.get('mode') if data.get('mode') in MODE_OK else 'preman'
	bahasa = data.get('bahasa') if data.get('bahasa') in BAHASA_OK else 'tetun'
	topik = str(data.get('topik', ''))[:40]
	if not pesan:
		return JsonResponse({'detail': 'pesan kosong'}, status=400)

	# TODO: SAMBUNGKAN KE QWEN + LoRA + XTTS DI SINI
	#   1) system = PERSONA[mode] + f" Bahasa belajar: {bahasa}. Topik: {topik}."  -> kirim ke model (Qwen + LoRA)
	#      (di proyek ini sudah ada ai/llm.py dengan backend 'local' untuk server Ollama/vLLM)
	#   2) minta model mengembalikan JSON {"jawaban": "...", "benar": true/false}
	#   3) opsional: ubah 'jawaban' jadi suara dengan XTTS dan kirim URL audio (browser lalu memutar audio itu,
	#      bukan SpeechSynthesis, supaya bahasa Tetun terdengar benar)
	#   4) batasi pemakaian per user (biaya/GPU) seperti di ai/views.py
	kunci = KUNCI_BENAR.get(topik, ())
	benar = any(k in pesan.lower() for k in kunci)
	return JsonResponse({'jawaban': MOCK[mode], 'benar': benar, 'lang': bahasa})
```

## Catatan jujur
- **Ini bukan video.** "Video call" dibuat dari pergantian 4 gambar (diam/ngomong/jempol/mikir) dengan animasi mulut 180 ms.
- **Suara** memakai `SpeechSynthesis` browser. Browser umumnya TIDAK punya suara Tetun, jadi Tetun dibacakan dengan suara Portugis (pt-PT) dan pelafalannya tidak sempurna. Mikrofon (`SpeechRecognition`) juga memakai pt-PT untuk Tetun; hanya Chrome/Edge/Safari terbaru, butuh HTTPS, dan audio bisa dikirim ke vendor browser. XTTS (TTS server) adalah jalan keluar untuk suara Tetun yang benar.
- **Poin** dihitung di browser (localStorage) hanya untuk tampilan. Jangan dijadikan nilai resmi: pengguna bisa mengubahnya. Bila poin perlu dipercaya, simpan dan hitung di server.
- Browser memutar suara hanya setelah ada sentuhan pengguna, jadi sapaan awal hanya tampil sebagai teks; sapaan bersuara terdengar saat mode diganti.
- Endpoint contoh hanya tiruan, belum ada model sungguhan di balik `/api/lafex-chat/`.
