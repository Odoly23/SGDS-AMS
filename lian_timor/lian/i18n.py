"""
Semua teks antarmuka dalam 4 bahasa: tet (Tetun), en, pt, id.

CATATAN PENTING: terjemahan Tetun dan Portugis di sini ditulis oleh AI sebagai DRAF.
Mohon dicek penutur asli sebelum dipakai umum. Cukup edit teks di file ini.

Pemakaian di template:  {% t "rekam" %}   ->  keempat bahasa dirender, CSS hanya menampilkan yang dipilih.
Dengan begitu ganti bahasa = 1 klik, tanpa memuat ulang halaman, dan tetap jalan saat offline.
"""
KODE = ("tet", "en", "pt", "id")

TEKS = {
    "app_name": dict(tet="Lian Timor", en="Lian Timor", pt="Lian Timor", id="Lian Timor"),
    "app_tagline": dict(tet="Aprende lian Timor", en="Learn the languages of Timor-Leste",
                        pt="Aprende as línguas de Timor-Leste", id="Belajar bahasa Timor-Leste"),
    "skip": dict(tet="Ba konteúdu", en="Skip to content", pt="Saltar para o conteúdo", id="Lompat ke isi"),
    "lang_label": dict(tet="Lian", en="Language", pt="Língua", id="Bahasa"),
    # navigasi bawah
    "nav_home": dict(tet="Uma", en="Home", pt="Início", id="Beranda"),
    "nav_learn": dict(tet="Aprende", en="Learn", pt="Aprender", id="Belajar"),
    "nav_talk": dict(tet="Ko'alia", en="Talk", pt="Falar", id="Bicara"),
    "nav_help": dict(tet="Ajuda AI", en="Help AI", pt="Ajudar IA", id="Bantu AI"),
    "nav_account": dict(tet="Konta", en="Account", pt="Conta", id="Akun"),
    # menu beranda
    "menu_talk": dict(tet="KO'ALIA HO AI", en="TALK WITH AI", pt="FALAR COM A IA", id="BICARA DENGAN AI"),
    "menu_learn": dict(tet="APRENDE", en="LEARN", pt="APRENDER", id="BELAJAR"),
    "menu_help": dict(tet="AJUDA AI", en="HELP TRAIN AI", pt="AJUDAR A IA", id="BANTU LATIH AI"),
    "menu_account": dict(tet="HA'U NIA KONTA", en="MY ACCOUNT", pt="MINHA CONTA", id="AKUN SAYA"),
    "sub_talk": dict(tet="Ko'alia, lafaek sei hatán", en="Speak, the crocodile answers",
                     pt="Fala, o crocodilo responde", id="Bicara, si buaya menjawab"),
    "sub_learn": dict(tet="Merkadu, hasoru malu, eskola", en="Market, greetings, school",
                      pt="Mercado, cumprimentos, escola", id="Pasar, sapaan, sekolah"),
    "sub_help": dict(tet="Grava ita nia lian, ajuda AI aprende", en="Record your language, help AI learn",
                     pt="Grava a tua língua, ajuda a IA a aprender", id="Rekam bahasamu, bantu AI belajar"),
    "sub_account": dict(tet="Ha'u nia progresu", en="Your progress", pt="O teu progresso", id="Kemajuanmu"),
    "today_title": dict(tet="Ohin atu aprende saida?", en="What do you want to learn today?",
                        pt="O que queres aprender hoje?", id="Hari ini belajar apa?"),
    "kalimat_n": dict(tet="{n} fraze", en="{n} sentences", pt="{n} frases", id="{n} kalimat"),
    "level": dict(tet="Nivel", en="Level", pt="Nível", id="Level"),
    "coming_soon_badge": dict(tet="Sei mai lalais", en="Coming soon", pt="Em breve", id="Segera hadir"),
    # tombol umum
    "start": dict(tet="Hahú", en="Start", pt="Começar", id="Mulai"),
    "record": dict(tet="Grava", en="Record", pt="Gravar", id="Rekam"),
    "listen": dict(tet="Rona", en="Listen", pt="Ouvir", id="Dengar"),
    "send": dict(tet="Haruka", en="Send", pt="Enviar", id="Kirim"),
    "thanks": dict(tet="Obrigadu!", en="Thank you!", pt="Obrigado!", id="Terima kasih!"),
    "back_home": dict(tet="Fila ba uma", en="Back home", pt="Voltar ao início", id="Kembali ke beranda"),
    "install_hint": dict(tet="Tau iha ekran uma", en="Add to home screen", pt="Adicionar ao ecrã inicial",
                         id="Pasang di layar utama"),
    # halaman sementara & offline
    "soon_title": dict(tet="Sei mai lalais", en="Coming soon", pt="Em breve", id="Segera hadir"),
    "soon_text": dict(tet="Pájina ne'e sei prontu lalais.", en="This page will be ready soon.",
                      pt="Esta página estará pronta em breve.", id="Halaman ini segera siap."),
    "offline_title": dict(tet="La iha internet", en="No internet", pt="Sem internet", id="Tidak ada internet"),
    "offline_text": dict(tet="Ita la iha internet. Pájina ne'ebé ita loke ona sei servisu.",
                         en="You are offline. Pages you opened before still work.",
                         pt="Estás sem internet. As páginas que já abriste continuam a funcionar.",
                         id="Kamu sedang offline. Halaman yang pernah dibuka tetap bisa dipakai."),
}


def ambil(kunci, bahasa="tet", **format_args):
    """Ambil satu teks (dipakai di Python/tes). Jatuh ke Tetun bila bahasa tidak ada."""
    teks = TEKS[kunci].get(bahasa) or TEKS[kunci]["tet"]
    return teks.format(**format_args) if format_args else teks
