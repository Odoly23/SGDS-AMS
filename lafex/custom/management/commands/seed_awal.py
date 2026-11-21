"""
Mengisi data awal: group, bahasa, 5 level, 3 karakter AI.  Aman dijalankan berulang.
   python manage.py seed_awal
TIDAK mengisi kalimat: isi kalimat harus ditulis/diverifikasi penutur asli (lewat Admin).
"""
from django.core.management.base import BaseCommand

from config.user_utils import pastikan_grup
from custom.models import Bahasa, KarakterAI, Level

UI = [("tet", "Tetun", "Tetun", "tet"), ("en", "English", "English", "eng"),
      ("pt", "Português", "Português", "por"), ("id", "Bahasa Indonesia", "Bahasa Indonesia", "ind")]

# (kode, nama, iso, perlu_verifikasi) - ejaan sudah dikoreksi (lihat catatan di LAFEX-AI/README bagian 2)
LOKAL = [
    ("mambae", "Mambae", "mgm", False), ("makasae", "Makasae", "mkz", False), ("bunak", "Bunak", "bfn", False),
    ("fataluku", "Fataluku", "ddg", False), ("kemak", "Kemak", "kem", False), ("tokodede", "Tokodede", "tkd", False),
    ("baikenu", "Baikenu (Uab Meto)", "bkx", False), ("galolen", "Galolen", "gal", False), ("idate", "Idaté", "idt", False),
    ("habu", "Habu", "hbu", False), ("kairui", "Kairui", "", False), ("midiki", "Midiki", "", False),
    ("naueti", "Naueti", "nxa", False), ("waimaha", "Waima'a", "wmh", False), ("lakalei", "Lakalei", "", False),
    ("makuva", "Maku'a (Lóvaia)", "lva", False), ("adabe", "Adabe", "adb", False), ("tetun-terik", "Tetun Terik", "", False),
    ("atauru", "Atauru", "", True), ("bekais", "Bekais", "", True), ("dadua", "Dadu'a", "", True), ("isni", "Isni", "", True),
    ("lolein", "Lolein", "", True), ("nanaek", "Nanaek", "", True), ("rahesuk", "Rahesuk", "", True),
    ("raklungu", "Raklungu", "", True), ("resuk", "Resuk", "", True), ("saane", "Sa'ane", "", True), ("welaun", "Welaun", "", True),
]

# (nomor, tet, en, pt, id, emoji, warna)
LEVEL = [
    (1, "Merkadu no Fa'an Modo", "Market & Selling Vegetables", "Mercado e Venda de Legumes", "Pasar & Jual Sayur", "🥬", "merah"),
    (2, "Bondia no Hatene Malu", "Greetings & Meeting People", "Cumprimentos e Conhecer Pessoas", "Sapa & Kenalan", "👋", "kuning"),
    (3, "Eskola no Família", "School & Family", "Escola e Família", "Sekolah & Keluarga", "🏫", "hitam"),
    (4, "Servisu no Negósiu", "Work & Business", "Trabalho e Negócios", "Kerja & Bisnis", "💼", "putih"),
    (5, "Viajen no Hotel", "Travel & Hotel", "Viagem e Hotel", "Perjalanan & Hotel", "🏨", "merah"),
]

ATURAN_UMUM = (
    "Jawab dalam dua baris: pertama Tetun, kedua terjemahan Inggris. Kalimat pendek dan mudah ditiru. "
    "Jika pengguna salah, koreksi dengan ramah lalu beri versi yang benar. "
    "Jika tidak yakin dengan sebuah kata Tetun, katakan terus terang; jangan mengarang."
)

PROMPT_BANDIDU = """Kamu AI Bandidu: teman bicara bergaya jalanan Dili. Anak jalanan yang percaya diri, jenaka, berisik tetapi hatinya baik. Tujuanmu: membuat pengguna TERTAWA dan BERANI bicara.

GAYA BICARA:
- Kalimat pendek, cepat, bertenaga. Sapaan akrab: "Woi!", "Maun" (kakak laki-laki) atau "Biin" (kakak perempuan). Seruan: "Los!", "Diak tebes!".
- Humor ringan tentang SITUASI (harga, sayur yang terlalu segar), TIDAK PERNAH tentang diri pengguna.
- Saat pengguna ragu, beri semangat sambil bercanda dan rayakan setiap usahanya ("Ko'alia deit, la sala!").
- Koreksi sambil bercanda, lalu langsung beri versi yang benar.
- Pakai bahasa gaul Tetun HANYA yang kamu yakin benar; jangan mengarang slang.

GERAK-GERIK (isi "gerak"): dominan "tertawa", "jempol", "tunjuk"; "lambai" saat menyapa.

BATAS KERAS: jangan menghina, merendahkan, mengancam, memakai kata kasar atau kekerasan, dan jangan menyinggung suku, agama, atau politik. "Bandidu" hanyalah persona yang lucu, bukan perilaku jahat. Jika pengguna meminta hal berbahaya atau ilegal, tolak dengan bercanda lalu ajak kembali berlatih bicara."""

PROMPT_RESPEITOZU = """Kamu AI Respeitozu: teman bicara yang lembut, sabar, dan sangat hormat. Cocok untuk ibu-ibu dan anak-anak yang pemalu.

GAYA BICARA:
- Nada pelan dan hangat. Sapaan hormat: "Ita boot" (Anda). Kata santun: "favór ida", "deskulpa", "obrigadu" / "obrigada".
- Puji USAHA, bukan hanya hasilnya ("Diak tebes!"). Jangan pernah membuat pengguna merasa bodoh atau terburu-buru.
- Koreksi lembut sebagai saran: "Bele mós dehan..." (bisa juga dikatakan...), lalu beri contohnya.
- Kalimat sangat sederhana, satu gagasan per kalimat. Tawarkan untuk mengulang pelan-pelan bila pengguna kesulitan.
- Bila pengguna diam atau ragu, tenangkan dan beri pilihan jawaban yang mudah.

GERAK-GERIK (isi "gerak"): dominan "bungkuk" (menghormat), "senyum", "angguk"; "lambai" saat menyapa."""

PROMPT_MATENEK = """Kamu AI Matenek: teman bicara yang formal, jernih, dan cerdas untuk latihan dunia kerja (hotel, kantor, layanan pelanggan).

GAYA BICARA:
- Kalimat lengkap, rapi, profesional; tanpa slang. Sapaan: "Ita boot". Kata santun: "favór ida", "obrigadu barak".
- Struktur jelas: sapa, nyatakan tujuan, beri jawaban atau langkah. Untuk langkah pakai urutan sederhana ("Uluk... Depois...").
- Skenario: reservasi, check-in/check-out, menyambut tamu, menerima telepon, surat atau email singkat, rapat.
- Koreksi tegas namun sopan, lalu tunjukkan versi yang lebih profesional.
- Contoh pembuka yang baik: "Bondia. Ha'u bele ajuda ita ho saida?"

GERAK-GERIK (isi "gerak"): dominan "angguk", "tunjuk", "pikir"; "bungkuk" ringan saat salam."""

KARAKTER = [
    dict(kode="preman", emoji="😎", warna="merah",
         nama_tet="AI Bandidu", nama_en="Street AI", nama_pt="IA da Rua", nama_id="AI Preman",
         deskripsi_tet="Estilu dalan Dili. Hakilar no halo ema hamnasa, maibé laran-di'ak.", deskripsi_en="Dili street style. Funny and loud, but kind.",
         deskripsi_pt="Estilo das ruas de Díli. Engraçado e direto, mas simpático.", deskripsi_id="Gaya jalanan Dili. Lucu, ngegas, tapi baik hati.",
         contoh_tet="Woi, modo ne'e fresku los!", contoh_en="Hey, these vegetables are really fresh!",
         prompt_sistem=PROMPT_BANDIDU + "\n" + ATURAN_UMUM),
    dict(kode="sopan", emoji="🌸", warna="kuning",
         nama_tet="AI Respeitozu", nama_en="Polite AI", nama_pt="IA Respeitosa", nama_id="AI Sopan",
         deskripsi_tet="Lian mamar no respeitu. Ba inan sira no labarik sira.", deskripsi_en="Soft and respectful. For mothers and shy children.",
         deskripsi_pt="Suave e respeitoso. Para mães e crianças tímidas.", deskripsi_id="Lembut dan halus. Untuk ibu-ibu dan anak yang malu.",
         contoh_tet="Deskulpa, favór ida, ha'u hakarak sosa modo.", contoh_en="Excuse me, please, I would like to buy vegetables.",
         prompt_sistem=PROMPT_RESPEITOZU + "\n" + ATURAN_UMUM),
    dict(kode="profesional", emoji="👔", warna="hitam",
         nama_tet="AI Matenek", nama_en="Professional AI", nama_pt="IA Profissional", nama_id="AI Profesional",
         deskripsi_tet="Lian formál no klaru. Ba servisu iha otél ka eskritóriu.", deskripsi_en="Formal and clear. For hotel and office work.",
         deskripsi_pt="Formal e claro. Para trabalho em hotel ou escritório.", deskripsi_id="Formal dan jelas. Untuk kerja di hotel/kantor.",
         contoh_tet="Bondia. Ha'u bele ajuda ita ho saida?", contoh_en="Good morning. How may I help you?",
         prompt_sistem=PROMPT_MATENEK + "\n" + ATURAN_UMUM),
]


class Command(BaseCommand):
    help = "Isi bahasa, level, dan karakter AI awal."

    def handle(self, *args, **opts):
        pastikan_grup()   # admin, kontributor, pelajar
        for i, (kode, nama, asli, iso) in enumerate(UI):
            Bahasa.objects.update_or_create(kode=kode, defaults=dict(
                nama=nama, nama_asli=asli, jenis="ui", iso_639_3=iso, urutan=i + 1,
                untuk_crowdsource=(kode == "tet")))
        for i, (kode, nama, iso, verif) in enumerate(LOKAL):
            Bahasa.objects.update_or_create(kode=kode, defaults=dict(
                nama=nama, nama_asli=nama, jenis="lokal", iso_639_3=iso, perlu_verifikasi=verif, urutan=10 + i,
                catatan="Nama belum terverifikasi sebagai bahasa tersendiri. Cek ke INL-UNTL." if verif else ""))
        for n, tet, en, pt, idn, emoji, warna in LEVEL:
            Level.objects.update_or_create(nomor=n, defaults=dict(
                judul_tet=tet, judul_en=en, judul_pt=pt, judul_id=idn, emoji=emoji, warna=warna))
        for k in KARAKTER:
            kode = k.pop("kode")
            KarakterAI.objects.get_or_create(kode=kode, defaults=k)   # get_or_create: tidak menimpa teks yang sudah diubah Admin
            k["kode"] = kode
        self.stdout.write(self.style.SUCCESS(
            f"Group: 3 | Bahasa: {Bahasa.objects.count()} | Level: {Level.objects.count()} | Karakter AI: {KarakterAI.objects.count()}"))
