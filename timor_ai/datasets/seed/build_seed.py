"""
Membuat seed_data.json + seed_phrases.csv dari daftar di bawah.
Jalankan:  python datasets/seed/build_seed.py

PENTING (kejujuran data):
- Tetun / Portugis / Inggris di bawah adalah DRAFT yang ditulis oleh AI. Wajib dicek penutur asli
  (status awal = "draft").
- Mambae & Makasae SENGAJA KOSONG. Kami tidak mau mengarang kalimat bahasa daerah. Kolom ini
  diisi oleh penutur asli lewat Django Admin / CSV (lihat README, bagian crowdsourcing).
"""
import csv
import json
from pathlib import Path

# (kategori, tetun, portugis, inggris)
DATA = {
"greeting": [
 ("Bondia!", "Bom dia!", "Good morning!"),
 ("Botarde!", "Boa tarde!", "Good afternoon!"),
 ("Bonoite!", "Boa noite!", "Good evening!"),
 ("Diak ka lae?", "Tudo bem?", "How are you?"),
 ("Ha'u diak.", "Estou bem.", "I am fine."),
 ("Obrigadu.", "Obrigado.", "Thank you."),
 ("Ha'u nia naran Maria.", "O meu nome é Maria.", "My name is Maria."),
 ("Ita nia naran saida?", "Qual é o seu nome?", "What is your name?"),
 ("Ha'u mai husi Dili.", "Venho de Díli.", "I come from Dili."),
 ("Ita hela iha ne'ebé?", "Onde mora?", "Where do you live?"),
 ("Kontente hasoru ita.", "Prazer em conhecê-lo.", "Nice to meet you."),
 ("Ita hasoru malu fali tan.", "Até logo.", "See you later."),
 ("Deskulpa.", "Desculpe.", "Sorry. / Excuse me."),
 ("Favór ida.", "Por favor.", "Please."),
 ("Ha'u la komprende.", "Não compreendo.", "I do not understand."),
 ("Favór ida ko'alia neineik.", "Fale devagar, por favor.", "Please speak slowly."),
 ("Ita bele ko'alia Tetun?", "Pode falar Tetum?", "Can you speak Tetun?"),
 ("Parabéns!", "Parabéns!", "Congratulations!"),
 ("Natál diak!", "Feliz Natal!", "Merry Christmas!"),
 ("Ita bele ajuda ha'u?", "Pode ajudar-me?", "Can you help me?"),
],
"market": [
 ("Ida ne'e hira?", "Quanto custa isto?", "How much is this?"),
 ("Ida ne'e karun liu.", "Isto é muito caro.", "This is too expensive."),
 ("Bele fo diskontu?", "Pode fazer desconto?", "Can you give a discount?"),
 ("Ha'u hakarak sosa paun.", "Quero comprar pão.", "I want to buy bread."),
 ("Ha'u hakarak sosa modo.", "Quero comprar legumes.", "I want to buy vegetables."),
 ("Ha'u hakarak sosa foos kilu rua.", "Quero comprar dois quilos de arroz.", "I want to buy two kilos of rice."),
 ("Iha troka ka lae?", "Tem troco?", "Do you have change?"),
 ("Ha'u selu ho dolar.", "Pago em dólares.", "I pay in dollars."),
 ("Ida ne'e baratu.", "Isto é barato.", "This is cheap."),
 ("Ha'u hakarak sosa ikan.", "Quero comprar peixe.", "I want to buy fish."),
 ("Ha'u hakarak sosa manu.", "Quero comprar galinha.", "I want to buy chicken."),
 ("Ikan ne'e fresku ka lae?", "Este peixe é fresco?", "Is this fish fresh?"),
 ("Fo ida ba ha'u.", "Dê-me um.", "Give me one."),
 ("Merkadu loke oras hira?", "A que horas abre o mercado?", "What time does the market open?"),
 ("Ha'u la iha osan ona.", "Já não tenho dinheiro.", "I have no more money."),
 ("Ha'u hakarak sosa ai-farina.", "Quero comprar mandioca.", "I want to buy cassava."),
 ("Kafé ida hira?", "Quanto custa um café?", "How much is a coffee?"),
 ("Ha'u hakarak sosa hahán.", "Quero comprar comida.", "I want to buy food."),
 ("Hira ida-ida?", "Quanto é cada um?", "How much is each one?"),
 ("Obrigadu, ha'u sei mai fali.", "Obrigado, volto mais tarde.", "Thank you, I will come back later."),
],
"family": [
 ("Ne'e ha'u nia inan.", "Esta é a minha mãe.", "This is my mother."),
 ("Ne'e ha'u nia aman.", "Este é o meu pai.", "This is my father."),
 ("Ha'u iha maun ida.", "Tenho um irmão mais velho.", "I have one older brother."),
 ("Ha'u iha biin ida.", "Tenho uma irmã mais velha.", "I have one older sister."),
 ("Ha'u iha alin rua.", "Tenho dois irmãos mais novos.", "I have two younger siblings."),
 ("Ha'u nia avó hela iha foho.", "A minha avó vive na montanha.", "My grandmother lives in the mountains."),
 ("Ha'u nia família boot.", "A minha família é grande.", "My family is big."),
 ("Ha'u kaben ona.", "Sou casado.", "I am married."),
 ("Ha'u iha oan mane ida.", "Tenho um filho.", "I have a son."),
 ("Ha'u iha oan feto ida.", "Tenho uma filha.", "I have a daughter."),
 ("Ita nia família iha ema hira?", "Quantas pessoas há na sua família?", "How many people are in your family?"),
 ("Ha'u nia tiu hela iha Baucau.", "O meu tio vive em Baucau.", "My uncle lives in Baucau."),
 ("Ne'e ha'u nia belun diak.", "Este é o meu bom amigo.", "This is my good friend."),
 ("Ami han hamutuk iha uma.", "Comemos juntos em casa.", "We eat together at home."),
 ("Ha'u nia inan tein hahán.", "A minha mãe cozinha.", "My mother cooks."),
 ("Ha'u nia aman serbisu iha to'os.", "O meu pai trabalha no campo.", "My father works in the field."),
 ("Labarik sira brinka iha liur.", "As crianças brincam lá fora.", "The children play outside."),
 ("Ha'u ba vizita ha'u nia família iha knua.", "Vou visitar a minha família na aldeia.", "I am going to visit my family in the village."),
 ("Ami selebra festa família.", "Celebramos uma festa de família.", "We celebrate a family party."),
 ("Ha'u hadomi ha'u nia família.", "Amo a minha família.", "I love my family."),
],
"school": [
 ("Ha'u estuda iha eskola.", "Estudo na escola.", "I study at school."),
 ("Ha'u nia profesór diak tebes.", "O meu professor é muito bom.", "My teacher is very good."),
 ("Ha'u la hatene.", "Não sei.", "I do not know."),
 ("Ha'u hakarak aprende Inglés.", "Quero aprender inglês.", "I want to learn English."),
 ("Ita iha livru ka lae?", "Tem um livro?", "Do you have a book?"),
 ("Ohin iha teste matemátika.", "Hoje há teste de matemática.", "Today there is a mathematics test."),
 ("Haree ba kuadru.", "Olhem para o quadro.", "Look at the board."),
 ("Hakerek ita nia naran iha folha ne'e.", "Escreve o teu nome nesta folha.", "Write your name on this sheet."),
 ("Lee livru ne'e.", "Lê este livro.", "Read this book."),
 ("Ha'u halo ona tarefa.", "Fiz o trabalho de casa.", "I did my homework."),
 ("Eskola hahú oras hira?", "A que horas começa a escola?", "What time does school start?"),
 ("Oras intervalu ona.", "É hora do intervalo.", "It is break time."),
 ("Ha'u nia eskola besik ha'u nia uma.", "A minha escola fica perto de casa.", "My school is near my house."),
 ("Ha'u hakarak sai profesór.", "Quero ser professor.", "I want to become a teacher."),
 ("Ha'u estuda iha universidade.", "Estudo na universidade.", "I study at university."),
 ("Ita nia klase iha ne'ebé?", "Onde é a sua sala de aula?", "Where is your classroom?"),
 ("Ha'u hetan nota diak.", "Tirei uma boa nota.", "I got a good grade."),
 ("Labarik sira ba eskola loron-loron.", "As crianças vão à escola todos os dias.", "The children go to school every day."),
 ("Favór ida, hatete fali.", "Por favor, repita.", "Please repeat."),
 ("Ha'u presiza kaneta no kadernu.", "Preciso de caneta e caderno.", "I need a pen and a notebook."),
],
"health": [
 ("Ha'u moras.", "Estou doente.", "I am sick."),
 ("Ha'u nia ulun moras.", "Dói-me a cabeça.", "I have a headache."),
 ("Ha'u nia kabun moras.", "Dói-me a barriga.", "I have a stomachache."),
 ("Ha'u nia isin manas.", "Tenho febre.", "I have a fever."),
 ("Ha'u presiza ba klínika.", "Preciso de ir à clínica.", "I need to go to the clinic."),
 ("Hospitál iha ne'ebé?", "Onde fica o hospital?", "Where is the hospital?"),
 ("Ha'u presiza doutór.", "Preciso de um médico.", "I need a doctor."),
 ("Ha'u presiza aimoruk.", "Preciso de medicamento.", "I need medicine."),
 ("Hemu bé barak.", "Beba muita água.", "Drink a lot of water."),
 ("Ha'u iha alergia.", "Tenho alergia.", "I have an allergy."),
 ("Ha'u isin-rua.", "Estou grávida.", "I am pregnant."),
 ("Ha'u presiza vasina.", "Preciso de uma vacina.", "I need a vaccine."),
 ("Fase liman ho sabaun.", "Lava as mãos com sabão.", "Wash your hands with soap."),
 ("Ha'u la bele iis diak.", "Não consigo respirar bem.", "I cannot breathe well."),
 ("Ha'u kanek.", "Estou ferido.", "I am injured."),
 ("Ha'u nia nehan moras.", "Dói-me o dente.", "I have a toothache."),
 ("Husi bainhira ita sente moras?", "Desde quando se sente doente?", "Since when have you felt ill?"),
 ("Ha'u presiza ambulánsia.", "Preciso de uma ambulância.", "I need an ambulance."),
 ("Ha'u sente di'ak liu ona.", "Já me sinto melhor.", "I feel better now."),
 ("Han aimoruk ne'e dala tolu loron-loron.", "Tome este medicamento três vezes por dia.", "Take this medicine three times a day."),
],
}

OUT = Path(__file__).parent
phrases = []
for cat, rows in DATA.items():
    assert len(rows) == 20, (cat, len(rows))
    for i, (tet, por, eng) in enumerate(rows, 1):
        phrases.append({
            "code": f"{cat}-{i:03d}",
            "category": cat,
            "translations": {"tet": tet, "por": por, "eng": eng, "mambae": "", "makasae": ""},
        })
assert len(phrases) == 100

doc = {
    "meta": {
        "version": 1,
        "languages": ["tet", "por", "eng", "mambae", "makasae"],
        "status_note": "tet/por/eng = DRAFT buatan AI, perlu dicek penutur asli. mambae/makasae = KOSONG, diisi komunitas.",
        "default_status": "draft",
        "default_source": "seed-ai-draft",
    },
    "phrases": phrases,
}
(OUT / "seed_data.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

with open(OUT / "seed_phrases.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["code", "category", "tet", "por", "eng", "mambae", "makasae"])
    for p in phrases:
        t = p["translations"]
        w.writerow([p["code"], p["category"], t["tet"], t["por"], t["eng"], t["mambae"], t["makasae"]])
print("OK:", len(phrases), "kalimat ditulis")
