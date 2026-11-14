"""
Mengisi Level 1 "Pasar & Jual Sayur": 4 materi x 5 kalimat = 20 kalimat (Tetun, English, Português, Indonesia).

   python manage.py seed_level1

PENTING: semua kalimat ini DRAF buatan AI (status 'draft'). Wajib dicek penutur asli, lalu ubah statusnya
menjadi 'terverifikasi' di Admin. Aman dijalankan berulang (tidak menimpa kalimat yang sudah diedit Admin).
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from belajar.models import Kalimat
from custom.models import Level, Materi

# (urutan materi, judul tet/en/pt/id, emoji, [ (emoji, tet, en, pt, id), ... ])
DATA = [
	(1, ("Hasoru ema sosa", "Greeting customers", "Receber os clientes", "Menyapa pembeli"), "👋", [
		("👋", "Bondia!", "Good morning!", "Bom dia!", "Selamat pagi!"),
		("🛒", "Ita hakarak sosa saida?", "What would you like to buy?", "O que quer comprar?", "Mau beli apa?"),
		("🥬", "Modo ne'e fresku.", "These vegetables are fresh.", "Estes legumes são frescos.", "Sayur ini segar."),
		("🧑‍🌾", "Ha'u fa'an modo.", "I sell vegetables.", "Eu vendo legumes.", "Saya jual sayur."),
		("🙏", "Obrigadu barak!", "Thank you very much!", "Muito obrigado!", "Terima kasih banyak!"),
	]),
	(2, ("Hatudu sasán", "Showing the goods", "Mostrar a mercadoria", "Menunjukkan barang"), "🌽", [
		("🌽", "Ha'u iha batar.", "I have corn.", "Tenho milho.", "Saya punya jagung."),
		("🌿", "Ai-farina ne'e fresku.", "This cassava is fresh.", "Esta mandioca é fresca.", "Singkong ini segar."),
		("👆", "Ita bele hili.", "You can choose.", "Pode escolher.", "Silakan pilih."),
		("🍌", "Hudi ne'e midar.", "These bananas are sweet.", "Estas bananas são doces.", "Pisang ini manis."),
		("🍠", "Fehuk ne'e boot.", "This sweet potato is big.", "Esta batata-doce é grande.", "Ubi ini besar."),
	]),
	(3, ("Folin", "Prices", "Preços", "Harga"), "💵", [
		("❓", "Ida ne'e hira?", "How much is this?", "Quanto custa isto?", "Ini berapa?"),
		("💵", "Ida ne'e dolar ida.", "This is one dollar.", "Isto custa um dólar.", "Ini satu dolar."),
		("💵", "Ida ne'e dolar rua.", "This is two dollars.", "Isto custa dois dólares.", "Ini dua dolar."),
		("👍", "Folin ne'e baratu.", "The price is cheap.", "O preço é barato.", "Harganya murah."),
		("🤝", "Bele fo diskontu uitoan.", "I can give a small discount.", "Posso fazer um pequeno desconto.", "Bisa kasih diskon sedikit."),
	]),
	(4, ("Selu no troka", "Paying and change", "Pagar e troco", "Bayar dan kembalian"), "🪙", [
		("💵", "Ita selu ho dolar?", "Are you paying with dollars?", "Paga em dólares?", "Bayar pakai dolar?"),
		("🪙", "Ha'u iha troka.", "I have change.", "Tenho troco.", "Saya punya uang kembalian."),
		("🙌", "Ne'e ita nia troka.", "Here is your change.", "Aqui está o seu troco.", "Ini kembaliannya."),
		("➕", "Ita hakarak sasán seluk tan?", "Do you want anything else?", "Quer mais alguma coisa?", "Mau yang lain lagi?"),
		("😊", "Mai fali tan!", "Come again!", "Volte sempre!", "Datang lagi ya!"),
	]),
]


class Command(BaseCommand):
	help = "Isi Level 1 (20 kalimat draf)."

	def handle(self, *args, **opts):
		if not Level.objects.filter(nomor=1).exists():
			call_command('seed_awal', verbosity=0)
		level = Level.objects.get(nomor=1)
		baru = 0
		for urutan, (jt, je, jp, ji), emoji, kalimat in DATA:
			materi, _ = Materi.objects.get_or_create(level=level, urutan=urutan, defaults=dict(
				judul_tet=jt, judul_en=je, judul_pt=jp, judul_id=ji, emoji=emoji))
			for i, (e, tet, en, pt, idn) in enumerate(kalimat, 1):
				_, dibuat = Kalimat.objects.get_or_create(materi=materi, urutan=i, defaults=dict(
					teks_tet=tet, teks_en=en, teks_pt=pt, teks_id=idn, emoji=e, status='draft'))
				baru += dibuat
		self.stdout.write(self.style.SUCCESS(
			f'Level 1: {Kalimat.objects.filter(materi__level=level).count()} kalimat ({baru} baru). Semua masih DRAF: mohon dicek penutur asli.'))
