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
    "nav_home": dict(tet="Varanda", en="Home", pt="Início", id="Beranda"),
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
    # ---- menu per group (gaya SJDF: VARANDA, UTILIZADORES, ...) ----
    "nav_users": dict(tet="Utilizadór", en="Users", pt="Utilizadores", id="Pengguna"),
    "nav_report": dict(tet="Relatóriu", en="Report", pt="Relatório", id="Laporan"),
    "nav_admin": dict(tet="Admin", en="Admin", pt="Admin", id="Admin"),
    "nav_logout": dict(tet="Sai", en="Log out", pt="Sair", id="Keluar"),
    "nav_menu": dict(tet="Menu", en="Menu", pt="Menu", id="Menu"),
    # ---- login / daftar ----
    "login_title": dict(tet="Tama", en="Sign in", pt="Entrar", id="Masuk"),
    "login_hint": dict(tet="Hakerek email ka nú. telefone", en="Type your email or phone number",
                       pt="Escreve o teu email ou número de telefone", id="Tulis email atau nomor HP"),
    "field_contact": dict(tet="Email ka nú. telefone", en="Email or phone number", pt="Email ou telefone", id="Email atau nomor HP"),
    "field_password": dict(tet="Palavra-pase", en="Password", pt="Palavra-passe", id="Kata sandi"),
    "field_password2": dict(tet="Hakerek fali palavra-pase", en="Type the password again", pt="Repete a palavra-passe", id="Ulangi kata sandi"),
    "btn_login": dict(tet="Tama", en="Sign in", pt="Entrar", id="Masuk"),
    "btn_register": dict(tet="Regista", en="Sign up", pt="Registar", id="Daftar"),
    "btn_guest": dict(tet="Kontinua la regista", en="Continue without signing up", pt="Continuar sem registo", id="Lanjut tanpa daftar"),
    "no_account": dict(tet="Seidauk iha konta?", en="No account yet?", pt="Ainda não tens conta?", id="Belum punya akun?"),
    "have_account": dict(tet="Iha konta ona?", en="Already have an account?", pt="Já tens conta?", id="Sudah punya akun?"),
    "register_title": dict(tet="Regista konta", en="Create account", pt="Criar conta", id="Buat akun"),
    "register_hint": dict(tet="Ita bele uza email ka nú. telefone", en="You can use an email or a phone number",
                          pt="Podes usar email ou telefone", id="Bisa pakai email atau nomor HP"),
    "guest_hint": dict(tet="Koko uluk, la presiza regista", en="Try it first, no sign-up needed",
                       pt="Experimenta primeiro, sem registo", id="Coba dulu, tidak perlu daftar"),
    "logout_title": dict(tet="Obrigadu! To'o tan", en="Thank you! See you soon", pt="Obrigado! Até breve", id="Terima kasih! Sampai jumpa"),
    "logout_text": dict(tet="Ita sai ona husi Lian Timor.", en="You have left Lian Timor.", pt="Saíste do Lian Timor.", id="Kamu sudah keluar dari Lian Timor."),
    # ---- "Kamu siapa?" ----
    "role_title": dict(tet="Ita nain sé?", en="Who are you?", pt="Quem és tu?", id="Kamu siapa?"),
    "role_anak": dict(tet="Labarik eskola", en="School student", pt="Aluno", id="Anak sekolah"),
    "role_dewasa": dict(tet="Ema boot", en="Adult", pt="Adulto", id="Dewasa"),
    "role_guru": dict(tet="Profesór", en="Teacher", pt="Professor", id="Guru"),
    "role_ibu_pasar": dict(tet="Inan iha merkadu", en="Mother at the market", pt="Mãe no mercado", id="Ibu di pasar"),
    # ---- akun ----
    "account_title": dict(tet="Ha'u nia konta", en="My account", pt="A minha conta", id="Akun saya"),
    "account_group": dict(tet="Grupu", en="Group", pt="Grupo", id="Grup"),
    "account_role": dict(tet="Ha'u mak", en="I am", pt="Eu sou", id="Saya adalah"),
    "account_guest": dict(tet="Konta tempu badak (konvidadu)", en="Temporary guest account", pt="Conta temporária de convidado",
                          id="Akun tamu sementara"),
    "account_change_role": dict(tet="Troka", en="Change", pt="Mudar", id="Ubah"),
    # ---- admin: utilizador & relatóriu ----
    "users_title": dict(tet="Lista utilizadór", en="User list", pt="Lista de utilizadores", id="Daftar pengguna"),
    "col_user": dict(tet="Utilizadór", en="User", pt="Utilizador", id="Pengguna"),
    "col_group": dict(tet="Grupu", en="Group", pt="Grupo", id="Grup"),
    "col_status": dict(tet="Estadu", en="Status", pt="Estado", id="Status"),
    "col_action": dict(tet="Asaun", en="Action", pt="Ação", id="Aksi"),
    "status_on": dict(tet="Ativu", en="Active", pt="Ativo", id="Aktif"),
    "status_off": dict(tet="Taka", en="Blocked", pt="Bloqueado", id="Dimatikan"),
    "btn_block": dict(tet="Taka", en="Block", pt="Bloquear", id="Matikan"),
    "btn_unblock": dict(tet="Loke", en="Unblock", pt="Desbloquear", id="Aktifkan"),
    "report_title": dict(tet="Relatóriu jerál", en="Overview", pt="Visão geral", id="Ringkasan"),
    "report_users": dict(tet="Utilizadór", en="Users", pt="Utilizadores", id="Pengguna"),
    "report_voices": dict(tet="Lian grava", en="Recorded voices", pt="Vozes gravadas", id="Suara terkumpul"),
    "report_pending": dict(tet="Hein", en="Pending", pt="Pendente", id="Menunggu"),
    "report_approved": dict(tet="Aprova", en="Approved", pt="Aprovado", id="Disetujui"),
    "report_per_lang": dict(tet="Lian grava tuir lian", en="Voices per language", pt="Vozes por língua", id="Suara per bahasa"),
    "report_empty": dict(tet="Seidauk iha lian grava.", en="No voices yet.", pt="Ainda não há vozes.", id="Belum ada suara."),
    "report_review": dict(tet="Rona no aprova iha Admin", en="Listen and approve in Admin", pt="Ouvir e aprovar no Admin", id="Dengar & setujui di Admin"),
    # ---- halaman galat ----
    "err404_title": dict(tet="Pájina la hetan", en="Page not found", pt="Página não encontrada", id="Halaman tidak ditemukan"),
    "err404_text": dict(tet="Pájina ne'e la existe, ka ita la iha lisensa atu loke.", en="This page does not exist, or you are not allowed to open it.",
                        pt="Esta página não existe, ou não tens permissão para a abrir.", id="Halaman ini tidak ada, atau kamu tidak punya izin membukanya."),
    "err500_title": dict(tet="Iha problema", en="Something went wrong", pt="Ocorreu um problema", id="Terjadi masalah"),
    "err500_text": dict(tet="Favór ida koko fali iha tempu badak.", en="Please try again in a moment.", pt="Tenta novamente daqui a pouco.", id="Silakan coba lagi sebentar lagi."),
    "footer_text": dict(tet="Aprende lian Timor-Leste", en="Learn the languages of Timor-Leste",
                        pt="Aprende as línguas de Timor-Leste", id="Belajar bahasa Timor-Leste"),

    # ---- pesan sistem & kesalahan (dirender 4 bahasa lewat {% pesan %}) ----
    "err_contact_invalid": dict(tet="Email ka nú. telefone la loos. Ezemplu: 7712 3456", en="Invalid email or phone number. Example: 7712 3456",
                                pt="Email ou telefone inválido. Exemplo: 7712 3456", id="Email atau nomor HP tidak valid. Contoh: 7712 3456"),
    "err_contact_taken": dict(tet="Kontaktu ne'e rejista ona. Favór tama.", en="This contact is already registered. Please sign in.",
                              pt="Este contacto já está registado. Entra, por favor.", id="Kontak ini sudah terdaftar. Silakan masuk."),
    "err_pw_short": dict(tet="Palavra-pase badak liu. Uza karakter 6 ka liu.", en="Password too short. Use at least 6 characters.",
                         pt="Palavra-passe demasiado curta. Usa pelo menos 6 caracteres.", id="Kata sandi terlalu pendek. Minimal 6 karakter."),
    "err_pw_common": dict(tet="Palavra-pase ne'e fásil liu. Hili seluk.", en="That password is too easy to guess. Choose another.",
                          pt="Essa palavra-passe é demasiado fácil. Escolhe outra.", id="Kata sandi terlalu mudah ditebak. Pilih yang lain."),
    "err_pw_mismatch": dict(tet="Palavra-pase la hanesan.", en="Passwords do not match.", pt="As palavras-passe não coincidem.", id="Kata sandi tidak sama."),
    "err_login_fail": dict(tet="Email/nú. telefone ka palavra-pase sala.", en="Wrong email/phone number or password.",
                           pt="Email/telefone ou palavra-passe errados.", id="Email/nomor HP atau kata sandi salah."),
    "err_login_locked": dict(tet="Koko barak liu ona. Hein minutu 15 no koko fali.", en="Too many attempts. Try again in 15 minutes.",
                             pt="Demasiadas tentativas. Tenta de novo daqui a 15 minutos.", id="Terlalu banyak percobaan. Coba lagi dalam 15 menit."),
    "err_guest_limit": dict(tet="Konta konvidadu barak liu husi rede ne'e. Koko fali tuir mai.", en="Too many guest accounts from this network. Try again later.",
                            pt="Demasiadas contas de convidado nesta rede. Tenta mais tarde.", id="Terlalu banyak akun tamu dari jaringan ini. Coba lagi nanti."),
    "msg_account_created": dict(tet="Konta foun kria ona.", en="New account created.", pt="Nova conta criada.", id="Akun baru dibuat."),
    "err_choose_one": dict(tet="Hili ida.", en="Choose one.", pt="Escolhe uma opção.", id="Pilih salah satu."),
    "err_admin_protect": dict(tet="Konta admin la bele taka husi pájina ne'e.", en="Admin accounts cannot be blocked from this page.",
                              pt="As contas de admin não podem ser bloqueadas nesta página.", id="Akun admin tidak bisa dimatikan dari halaman ini."),
    "msg_user_blocked": dict(tet="Utilizadór taka ona.", en="User blocked.", pt="Utilizador bloqueado.", id="Pengguna dimatikan."),
    "msg_user_unblocked": dict(tet="Utilizadór loke fali ona.", en="User unblocked.", pt="Utilizador desbloqueado.", id="Pengguna diaktifkan lagi."),

}


def ambil(kunci, bahasa="tet", **format_args):
    """Ambil satu teks (dipakai di Python/tes). Jatuh ke Tetun bila bahasa tidak ada."""
    teks = TEKS[kunci].get(bahasa) or TEKS[kunci]["tet"]
    return teks.format(**format_args) if format_args else teks
