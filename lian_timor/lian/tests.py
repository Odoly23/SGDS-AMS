"""Tes dasar Lian Timor. Jalankan: python manage.py test"""
import json
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.template import Context, Template
from django.test import TestCase, override_settings

from lian import i18n
from lian.models import (Bahasa, Kalimat, KarakterAI, Level, Materi, Pengguna, ProgresBelajar, RekamanSuara)


class TeksEmpatBahasa(TestCase):
    def test_semua_teks_lengkap_di_4_bahasa(self):
        for kunci, d in i18n.TEKS.items():
            for kode in i18n.KODE:
                self.assertTrue(d.get(kode), f"{kunci} belum ada terjemahan {kode}")

    def test_tag_t_merender_keempat_bahasa(self):
        html = Template('{% load lian_tags %}{% t "record" %}').render(Context())
        for kata in ("Grava", "Record", "Gravar", "Rekam"):   # contoh dari permintaan: Grava / Record / Rekam
            self.assertIn(kata, html)
        self.assertEqual(html.count('class="tx"'), 4)

    def test_tag_t_dengan_variabel_dan_escape(self):
        self.assertIn("20 kalimat", Template('{% load lian_tags %}{% t "kalimat_n" n=20 %}').render(Context()))

    def test_tag_ml_pakai_kolom_objek_dan_aman_dari_xss(self):
        lv = Level(nomor=1, judul_tet="<script>x</script>", judul_en="Market")
        html = Template('{% load lian_tags %}{% ml l "judul" %}').render(Context({"l": lv}))
        self.assertNotIn("<script>", html)
        self.assertIn("Market", html)
        self.assertEqual(i18n.ambil("record", "xx"), "Grava")   # bahasa tak dikenal -> Tetun


class Halaman(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_awal", verbosity=0)

    def test_semua_halaman_menu_terbuka(self):
        for nama in ("/", "/bicara/", "/belajar/", "/bantu-ai/", "/akun/", "/masuk/", "/offline/"):
            self.assertEqual(self.client.get(nama).status_code, 200, nama)

    def test_base_punya_topbar_tais_pilihan_bahasa_dan_tombol_buaya(self):
        html = self.client.get("/").content.decode()
        self.assertIn("tais-faixa", html)
        for kode in ("tet", "en", "pt", "id"):
            self.assertIn(f'data-set-lang="{kode}"', html)
        self.assertIn('class="bicara"', html)
        self.assertIn('<html lang="tet"', html)       # Tetun = bahasa utama

    def test_beranda_menampilkan_5_level(self):
        html = self.client.get("/").content.decode()
        for n in range(1, 6):
            self.assertIn(f"?level={n}", html)

    def test_pwa(self):
        r = self.client.get("/manifest.webmanifest")
        self.assertEqual(r["Content-Type"], "application/manifest+json")
        m = json.loads(r.content)
        self.assertEqual(m["display"], "standalone")
        self.assertEqual(m["name"], "Lian Timor - Belajar Bahasa Timor Leste")
        self.assertTrue(any(i.get("purpose") == "maskable" for i in m["icons"]))
        sw = self.client.get("/sw.js")
        self.assertEqual(sw["Service-Worker-Allowed"], "/")
        self.assertIn("javascript", sw["Content-Type"])
        self.assertIn("no-cache", sw["Cache-Control"])
        self.assertIn("/offline/", sw.content.decode())

    def test_sw_tidak_menyimpan_halaman_pribadi(self):
        self.assertIn("admin|akun|masuk", self.client.get("/sw.js").content.decode())


class Model(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_awal", verbosity=0)

    def test_seed_idempoten_dan_tidak_menimpa_edit_admin(self):
        k = KarakterAI.objects.get(kode="preman")
        k.prompt_sistem = "diubah admin"
        k.save()
        call_command("seed_awal", verbosity=0)
        self.assertEqual(KarakterAI.objects.get(kode="preman").prompt_sistem, "diubah admin")
        self.assertEqual((Level.objects.count(), KarakterAI.objects.count()), (5, 3))

    def test_empat_bahasa_aplikasi_dan_bahasa_daerah(self):
        self.assertEqual(set(Bahasa.objects.filter(jenis="ui").values_list("kode", flat=True)), {"tet", "en", "pt", "id"})
        self.assertTrue(Bahasa.objects.filter(kode="mambae", untuk_crowdsource=True).exists())
        self.assertTrue(Bahasa.objects.filter(kode="tet", untuk_crowdsource=True).exists())   # Tetun juga bisa dipilih di crowdsource
        self.assertTrue(Bahasa.objects.filter(kode="atauru", perlu_verifikasi=True).exists())

    def test_pengguna_kode_anonim_unik_dan_tamu(self):
        a = Pengguna.objects.create_user("a@x.com", email="a@x.com", password="x12345")
        b = Pengguna.objects.create_user("tamu1", is_tamu=True)
        self.assertNotEqual(a.kode_anonim, b.kode_anonim)
        self.assertEqual(len(a.kode_anonim), 12)
        self.assertEqual(a.bahasa_ui, "tet")
        self.assertFalse(b.has_usable_password())
        Pengguna.objects.create_user("c", telepon="+6707700000")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Pengguna.objects.create_user("d", telepon="+6707700000")

    def test_level_materi_kalimat_dan_hitungan(self):
        lv = Level.objects.get(nomor=1)
        mt = Materi.objects.create(level=lv, urutan=1, judul_tet="Tawar harga")
        Kalimat.objects.create(materi=mt, urutan=1, teks_tet="Ida ne'e hira?", teks_en="How much is this?")
        Kalimat.objects.create(materi=mt, urutan=2, teks_tet="Karun liu.", aktif=False)
        self.assertEqual(lv.total_kalimat, 1)             # kalimat nonaktif tidak dihitung
        k = Kalimat.objects.first()
        self.assertEqual(k.teks("en"), "How much is this?")
        self.assertEqual(k.teks("pt"), "Ida ne'e hira?")   # kosong -> jatuh ke Tetun
        self.assertEqual(k.level, lv)
        self.assertIn("1", self.client.get("/").content.decode())

    def test_level_hanya_1_sampai_5(self):
        with self.assertRaises(ValidationError):
            Level(nomor=6, judul_tet="x").full_clean()

    def test_satu_progres_per_kalimat(self):
        mt = Materi.objects.create(level=Level.objects.get(nomor=1), judul_tet="m")
        k = Kalimat.objects.create(materi=mt, teks_tet="a")
        u = Pengguna.objects.create_user("p")
        ProgresBelajar.objects.create(pengguna=u, kalimat=k)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProgresBelajar.objects.create(pengguna=u, kalimat=k)

    def test_tiga_karakter_ai_punya_aturan_aman(self):
        for k in KarakterAI.objects.all():
            self.assertTrue(k.prompt_sistem)
            self.assertTrue(k.nama("en") and k.deskripsi("pt"))
        preman = KarakterAI.objects.get(kode="preman")
        self.assertIn("jangan menghina", preman.prompt_sistem)
        self.assertEqual(preman.contoh_tet, "Woi, modo ne'e fresku los!")


class RekamanPrivasi(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_awal", verbosity=0)
        mt = Materi.objects.create(level=Level.objects.get(nomor=1), judul_tet="m")
        cls.k = Kalimat.objects.create(materi=mt, teks_tet="Bondia, hau hakarak fa'an modo", teks_en="Good morning, I want to sell vegetables")

    def _rekam(self, **kw):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            return RekamanSuara.objects.create(
                kalimat=self.k, bahasa=Bahasa.objects.get(kode="fataluku"), gaya=KarakterAI.objects.get(kode="sopan"),
                audio=SimpleUploadedFile("a.webm", b"x" * 100, content_type="audio/webm"), **kw)

    def test_rekaman_tidak_menyimpan_identitas(self):
        nama_kolom = {f.name for f in RekamanSuara._meta.get_fields()}
        for terlarang in ("nama", "telepon", "alamat", "email", "pengguna", "user"):
            self.assertNotIn(terlarang, nama_kolom)
        self.assertFalse(RekamanSuara._meta.get_field("pengirim_kode").is_relation)   # kode samaran, BUKAN relasi ke akun
        self.assertEqual(self._rekam().status, "menunggu")

    def test_batas_ukuran_suara(self):
        besar = SimpleUploadedFile("b.webm", b"x" * (3 * 1024 * 1024))
        r = RekamanSuara(kalimat=self.k, bahasa=Bahasa.objects.get(kode="fataluku"), gaya=KarakterAI.objects.get(kode="sopan"), audio=besar)
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            with self.assertRaises(ValidationError):
                r.full_clean()

    def test_admin_setujui_tolak_dan_matikan_pengirim(self):
        nakal = Pengguna.objects.create_user("nakal", email="n@x.com")
        adm = Pengguna.objects.create_superuser("adm", "adm@x.com", "pw12345")
        r = self._rekam(pengirim_kode=nakal.kode_anonim)
        r.tinjau("disetujui", adm)
        r.refresh_from_db()
        self.assertEqual((r.status, r.ditinjau_oleh), ("disetujui", adm))
        r.tinjau("ditolak", adm, "bising")
        r.refresh_from_db()
        self.assertEqual(r.alasan_tolak, "bising")
        # aksi Admin 'matikan pengirim' lewat halaman admin sungguhan
        self.client.force_login(adm)
        resp = self.client.post("/admin/lian/rekamansuara/", {"action": "matikan_pengirim", "_selected_action": [r.pk]}, follow=True)
        self.assertEqual(resp.status_code, 200)
        nakal.refresh_from_db()
        self.assertFalse(nakal.is_active)
        adm.refresh_from_db()
        self.assertTrue(adm.is_active)

    def test_halaman_admin_terbuka(self):
        adm = Pengguna.objects.create_superuser("adm", "adm@x.com", "pw12345")
        self.client.force_login(adm)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self._rekam()
        for m in ("pengguna", "bahasa", "level", "materi", "kalimat", "karakterai", "rekamansuara", "progresbelajar"):
            self.assertEqual(self.client.get(f"/admin/lian/{m}/").status_code, 200, m)
        self.assertEqual(self.client.get("/admin/lian/rekamansuara/add/").status_code, 403)   # suara hanya masuk lewat halaman crowdsource
