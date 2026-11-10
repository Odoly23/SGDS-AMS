"""Tes otomatis dasar. Jalankan: python manage.py test"""
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from chat.detect import detect_language
from chat.models import Language
from rag.services import chunk_text


class DetectTests(TestCase):
    def test_tetun(self):
        self.assertEqual(detect_language("Ha'u hakarak sosa paun iha merkadu"), "tet")

    def test_english(self):
        self.assertEqual(detect_language("Where is the nearest hospital please?"), "eng")


class ChunkTests(TestCase):
    def test_chunk(self):
        text = ("Kalimat contoh yang cukup panjang. " * 60)
        chunks = chunk_text(text, size=300, overlap=30)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 340 for c in chunks))


@override_settings(LAFEX_AI={**__import__("django.conf").conf.settings.LAFEX_AI, "LLM_BACKEND": "dummy", "EMBEDDING_BACKEND": "hash"})
class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_phrases", verbosity=0)
        cls.user = get_user_model().objects.create_user("tes", password="x12345678")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_languages(self):
        r = self.client.get("/api/languages/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("tet", [x["code"] for x in r.json()])

    def test_chat(self):
        r = self.client.post("/api/chat/", {"message": "Bondia", "language": "tet"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn("conversation_id", r.json())

    def test_translate_uses_memory(self):
        r = self.client.post("/api/chat/", {"message": "Bondia!", "language": "por", "mode": "translate", "source_language": "tet"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn("Bom dia", r.json()["reply"]["content"])

    def test_requires_login(self):
        self.assertEqual(APIClient().post("/api/chat/", {}, format="json").status_code, 403)

    def test_cannot_read_other_users_conversation(self):
        cid = self.client.post("/api/chat/", {"message": "Halo", "language": "tet"}, format="json").json()["conversation_id"]
        other = APIClient()
        other.force_authenticate(get_user_model().objects.create_user("lain", password="x12345678"))
        self.assertEqual(other.get(f"/api/conversations/{cid}/").status_code, 404)
