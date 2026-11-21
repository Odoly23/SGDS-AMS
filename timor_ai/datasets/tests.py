"""Tes crowdsourcing: kirim, periksa, naik antrean, verifikasi + hadiah poin."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from billing import services as billing
from chat.models import Language
from datasets import services
from datasets.models import Phrase, Translation, Vote

User = get_user_model()


def user(n):
    return User.objects.create_user(n, email=f"{n}@x.com", password="x12345678")


class CrowdTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_phrases", verbosity=0)

    def setUp(self):
        cache.clear()
        self.a, self.b, self.rev = user("a"), user("b"), user("rev")

    def _submit(self, who=None, text="Obrigadu-versi-mambae"):
        return services.submit(who or self.a, "greeting-001", "mambae", text)

    def test_task_has_sources_and_skips_own(self):
        task = services.next_task(self.a, "mambae")
        self.assertIsNotNone(task)
        self.assertTrue({"tet", "por", "eng"} <= {s["lang"] for s in task["sources"]})
        t = services.submit(self.a, task["phrase"], "mambae", "tes")
        again = services.next_task(self.a, "mambae")
        self.assertNotEqual(again["phrase"], t.phrase.code)

    def test_submit_validation(self):
        self._submit()
        with self.assertRaises(services.ContribError):
            self._submit(self.b, "  obrigadu-VERSI-mambae ")      # duplikat (abaikan huruf besar/spasi)
        with self.assertRaises(services.ContribError):
            services.submit(self.a, "greeting-001", "mambae", "   ")
        with self.assertRaises(services.ContribError):
            services.submit(self.a, "tidak-ada", "mambae", "x")

    def test_cannot_vote_own_or_twice_and_promotion_needs_3(self):
        t = self._submit()
        with self.assertRaises(services.ContribError):
            services.vote(self.a, t.pk, True)
        users = [user(f"v{i}") for i in range(3)]
        for u in users[:2]:
            services.vote(u, t.pk, True)
        t.refresh_from_db()
        self.assertEqual(t.status, Translation.Status.DRAFT)
        with self.assertRaises(services.ContribError):
            services.vote(users[0], t.pk, True)
        services.vote(users[2], t.pk, True)
        t.refresh_from_db()
        self.assertEqual(t.status, Translation.Status.REVIEW)    # naik antrean, BELUM verified
        self.assertEqual(Translation.objects.filter(status="verified", language__code="mambae").count(), 0)

    def test_verification_pays_once(self):
        t = self._submit()
        voters = [user(f"v{i}") for i in range(3)]
        for u in voters:
            services.vote(u, t.pk, True)
        before = billing.get_wallet(self.a).balance
        services.set_status(t, Translation.Status.VERIFIED, self.rev)
        services.set_status(t, Translation.Status.VERIFIED, self.rev)       # dipanggil lagi: tidak bayar ulang
        self.assertEqual(billing.get_wallet(self.a).balance, before + 50)
        self.assertEqual(billing.get_wallet(voters[0]).balance, 100 + 2)    # 100 poin percobaan + 2 hadiah
        t.refresh_from_db()
        self.assertTrue(t.rewarded)
        self.assertEqual(t.reviewed_by, self.rev)

    def test_reviewer_cannot_reward_self(self):
        t = self._submit(self.rev)
        before = billing.get_wallet(self.rev).balance
        services.set_status(t, Translation.Status.VERIFIED, self.rev)
        self.assertEqual(billing.get_wallet(self.rev).balance, before)

    def test_daily_cap(self):
        from django.test import override_settings
        from django.conf import settings

        with override_settings(CONTRIB={**settings.CONTRIB, "MAX_SUBMISSIONS_PER_DAY": 2}):
            services.submit(self.a, "greeting-001", "mambae", "a1")
            services.submit(self.a, "greeting-002", "mambae", "a2")
            with self.assertRaises(services.ContribError):
                services.submit(self.a, "greeting-003", "mambae", "a3")

    def test_api_flow_and_page(self):
        c = APIClient()
        c.force_authenticate(self.a)
        task = c.get("/api/contribute/next/?language=mambae").json()["task"]
        r = c.post("/api/contribute/", {"phrase": task["phrase"], "language": "mambae", "text": "tes"}, format="json")
        self.assertEqual(r.status_code, 201)
        c2 = APIClient()
        c2.force_authenticate(self.b)
        item = c2.get("/api/contribute/review/?language=mambae").json()["item"]
        self.assertEqual(item["text"], "tes")
        self.assertEqual(c2.post("/api/contribute/vote/", {"translation": item["translation"], "agree": True}, format="json").status_code, 200)
        self.assertIsNone(c2.get("/api/contribute/review/?language=mambae").json()["item"])
        stats = c.get("/api/contribute/stats/").json()
        self.assertEqual(stats["me"]["submitted"], 1)
        self.assertEqual(c.get("/api/contribute/next/?language=xx").status_code, 400)
        self.assertEqual(APIClient().get("/api/contribute/stats/").status_code, 403)
        self.client.force_login(self.a)
        self.assertEqual(self.client.get("/kontribusi/").status_code, 200)

    def test_leaderboard_hides_identity(self):
        t = self._submit()
        services.set_status(t, Translation.Status.VERIFIED, self.rev)
        lb = services.leaderboard(self.a)
        self.assertEqual(lb[0]["verified"], 1)
        self.assertNotIn("a@x.com", lb[0]["name"])
        self.assertTrue(lb[0]["me"])
