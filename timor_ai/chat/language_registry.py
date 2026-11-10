"""
Daftar bahasa LAFEX-AI + koreksi ejaan dari daftar awal.

Kolom `status`:
  "ok"      -> nama sudah umum dipakai di literatur linguistik Timor-Leste
  "verify"  -> belum bisa saya pastikan sebagai bahasa tersendiri (bisa dialek /
               nama desa / nama klan). WAJIB dicek ke INL-UNTL (Instituto Nacional
               de Linguística) atau Glottolog/Ethnologue sebelum dipakai resmi.

Kolom `kind`: official | working | national | variety
"""

# (code, name, native_name, kind, iso, status, catatan)
LANGUAGES = [
    # ---- Bahasa resmi & bahasa kerja ----
    ("tet", "Tetun", "Tetun", "official", "tet", "ok",
     "Bahasa resmi. Ejaan Tetun = 'Tetun' (bukan 'Tetum', itu ejaan Inggris/Portugis lama). Varian standar: Tetun Dili (Tetun Prasa)."),
    ("por", "Portugis", "Português", "official", "por", "ok", "Bahasa resmi."),
    ("eng", "Inggris", "English", "working", "eng", "ok", "Bahasa kerja (Konstitusi Pasal 159)."),
    ("ind", "Indonesia", "Bahasa Indonesia", "working", "ind", "ok", "Bahasa kerja (Konstitusi Pasal 159)."),
    # ---- Bahasa nasional / lokal ----
    ("tetun-terik", "Tetun Terik", "Tetun Terik", "variety", "", "ok",
     "Ini VARIAN Tetun (Tetun selatan / Tetun Terik), bukan bahasa terpisah. Daftar awal menulis 'Tetum Terik'."),
    ("mambae", "Mambae", "Mambae", "national", "mgm", "ok",
     "Muncul 2x di daftar awal; digabung. Punya banyak dialek (mis. Mambae Ainaro, Mambae Same)."),
    ("makasae", "Makasae", "Makasae", "national", "mkz", "ok", "Bahasa non-Austronesia (Papua), wilayah Baucau/Viqueque."),
    ("bunak", "Bunak", "Bunak", "national", "bfn", "ok", "Bahasa non-Austronesia (Papua), wilayah Bobonaro/Covalima."),
    ("fataluku", "Fataluku", "Fataluku", "national", "ddg", "ok", "Bahasa non-Austronesia (Papua), wilayah Lautém."),
    ("kemak", "Kemak", "Kemak", "national", "kem", "ok", "Wilayah Bobonaro/Ermera."),
    ("tokodede", "Tokodede", "Tokodede", "national", "tkd", "ok", "Wilayah Liquiçá."),
    ("baikenu", "Baikenu (Uab Meto)", "Baikenu", "national", "bkx", "ok",
     "Daftar awal: 'Baikeno'. Ejaan umum: 'Baikenu'. Kerabat dekat Dawan/Uab Meto di Timor Barat (Indonesia). Wilayah Oecusse."),
    ("galolen", "Galolen", "Galolen", "national", "gal", "ok", "Daftar awal: 'Galoli'. Nama bahasa: 'Galolen'."),
    ("idate", "Idaté", "Idaté", "national", "idt", "ok",
     "Daftar awal menulis 'Idalaka' DAN 'Idate' -> keduanya digabung jadi satu (Idaté; 'Idalaka' nama kelompok etnis)."),
    ("habu", "Habu", "Habu", "national", "hbu", "ok", "Daftar awal: 'Habun'. Ejaan umum: 'Habu'."),
    ("kairui", "Kairui", "Kairui", "national", "", "ok",
     "Sering dikelompokkan bersama Midiki sebagai 'Kairui-Midiki'. Cek apakah mau dipisah atau digabung."),
    ("midiki", "Midiki", "Midiki", "national", "", "ok", "Lihat catatan Kairui."),
    ("naueti", "Naueti", "Naueti", "national", "nxa", "ok", "Wilayah Viqueque."),
    ("waimaha", "Waima'a", "Waima'a", "national", "wmh", "ok", "Wilayah Baucau/Viqueque."),
    ("lakalei", "Lakalei", "Lakalei", "national", "", "ok", "Cek wilayah penutur & kode ISO di Glottolog / INL-UNTL."),
    ("makuva", "Maku'a (Lóvaia)", "Maku'a", "national", "lva", "ok",
     "Daftar awal: 'Makuva'. Ejaan umum: 'Maku'a' (juga 'Lóvaia'). Penutur sangat sedikit, terancam punah."),
    ("adabe", "Adabe", "Adabe", "national", "adb", "ok", "Penutur sangat sedikit. Cek wilayah penutur & kode ISO di Glottolog / INL-UNTL."),
    ("atauru", "Atauru", "Atauru", "national", "", "verify",
     "Mungkin merujuk ke Pulau Atauro (kemungkinan sama dengan Raklungu/Raklu Un). Verifikasi dulu."),
    # ---- Nama di daftar awal yang BELUM bisa diverifikasi ----
    ("bekais", "Bekais", "Bekais", "national", "", "verify", "Belum terverifikasi sebagai bahasa tersendiri. Cek INL-UNTL."),
    ("dadua", "Dadu'a", "Dadu'a", "national", "", "verify",
     "Daftar awal menulis 'Dadua' DAN 'Dadu'a' -> digabung. Kemungkinan terkait Pulau Atauro. Verifikasi."),
    ("isni", "Isni", "Isni", "national", "", "verify", "Belum terverifikasi. Bisa jadi dialek/nama lokal."),
    ("lolein", "Lolein", "Lolein", "national", "", "verify", "Belum terverifikasi. Bisa jadi dialek/nama lokal."),
    ("nanaek", "Nanaek", "Nanaek", "national", "", "verify", "Belum terverifikasi. Bisa jadi dialek/nama lokal."),
    ("rahesuk", "Rahesuk", "Rahesuk", "national", "", "verify", "Kemungkinan terkait Pulau Atauro. Verifikasi."),
    ("raklungu", "Raklungu", "Raklungu", "national", "", "verify", "Kemungkinan terkait Pulau Atauro. Verifikasi."),
    ("resuk", "Resuk", "Resuk", "national", "", "verify", "Kemungkinan terkait Pulau Atauro. Verifikasi."),
    ("saane", "Sa'ane", "Sa'ane", "national", "", "verify", "Belum terverifikasi. Bisa jadi dialek/nama lokal."),
    ("welaun", "Welaun", "Welaun", "national", "", "verify", "Belum terverifikasi. Bisa jadi dialek/nama lokal."),
]

# Peta kode kita -> kode untuk library langdetect
LANGDETECT_MAP = {"por": "pt", "eng": "en", "ind": "id"}
