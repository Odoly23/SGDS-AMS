"""Tes poin, voucher, backend model berbayar (dengan klien palsu), dan halaman login."""
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from billing import services
from billing.models import CreditTransaction, Package, Voucher
from chat import llm, prompts
from chat.models import Conversation

User = get_user_model()


def make_user(name="u1"):
    return User.objects.create_user(name, email=f"{name}@example.com", password="x12345678")


class WalletTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()

    def test_trial_credits_given_once(self):
        w = services.get_wallet(self.user)
        self.assertEqual(w.balance, 100)
        self.assertEqual(services.get_wallet(self.user).balance, 100)
        self.assertEqual(CreditTransaction.objects.filter(kind="trial").count(), 1)

    def test_charge_never_goes_negative(self):
        services.get_wallet(self.user)
        cost, balance = services.charge_usage(self.user, 10_000_000, 10_000_000)   # biaya raksasa
        self.assertEqual(balance, 0)
        self.assertEqual(cost, 100)

    def test_cost_formula(self):
        # 1.000 token masuk + 500 keluar @ $4/$20 per juta = $0.014, x3 margin x1000 poin/USD = 42 poin
        self.assertEqual(services.cost_in_credits(1000, 500), 42)


class VoucherTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.pkg = Package.objects.create(name="Paket 1 USD", price_usd=1, credits=1000)

    def test_redeem_once(self):
        code = services.generate_vouchers(self.pkg, 1, "tes")[0]
        r = services.redeem_voucher(self.user, code.lower().replace("-", " "))   # toleran huruf kecil/spasi
        self.assertEqual(r["balance"], 1100)
        with self.assertRaises(services.BillingError):
            services.redeem_voucher(self.user, code)

    def test_plain_code_not_stored(self):
        code = services.generate_vouchers(self.pkg, 1)[0]
        v = Voucher.objects.get()
        self.assertNotIn(code.replace("-", ""), v.code_hash)
        self.assertEqual(len(v.code_hint), 4)

    def test_wrong_codes_lock_user(self):
        for _ in range(5):
            with self.assertRaises(services.BillingError):
                services.redeem_voucher(self.user, "AAAA-BBBB-CCCC")
        code = services.generate_vouchers(self.pkg, 1)[0]
        with self.assertRaises(services.BillingError) as ctx:   # kode benar pun ditolak saat terkunci
            services.redeem_voucher(self.user, code)
        self.assertIn("15 menit", str(ctx.exception))

    def test_void_voucher_rejected(self):
        code = services.generate_vouchers(self.pkg, 1)[0]
        Voucher.objects.update(status=Voucher.Status.VOID)
        with self.assertRaises(services.BillingError):
            services.redeem_voucher(self.user, code)

    def test_make_vouchers_command(self):
        import os, tempfile
        out = os.path.join(tempfile.mkdtemp(), "v.csv")
        call_command("make_vouchers", package=self.pkg.pk, count=3, batch="kios", out=out, verbosity=0)
        self.assertEqual(Voucher.objects.count(), 3)
        self.assertEqual(len(open(out, encoding="utf-8-sig").read().strip().splitlines()), 4)


class ApiBillingTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("seed_phrases", verbosity=0)
        self.user = make_user()
        self.c = APIClient()
        self.c.force_authenticate(self.user)

    def test_chat_charges_points_and_returns_balance(self):
        r = self.c.post("/api/chat/", {"message": "Bondia", "language": "tet"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertGreaterEqual(r.json()["credits_charged"], 1)
        self.assertEqual(r.json()["balance"], 100 - r.json()["credits_charged"])

    def test_memory_translation_is_free(self):
        r = self.c.post("/api/chat/", {"message": "Bondia!", "language": "por", "mode": "translate", "source_language": "tet"}, format="json")
        self.assertEqual(r.json()["credits_charged"], 0)
        self.assertEqual(r.json()["balance"], 100)

    def test_out_of_credits_returns_402(self):
        w = services.get_wallet(self.user)
        w.balance = 5
        w.save()
        r = self.c.post("/api/chat/", {"message": "Halo", "language": "tet"}, format="json")
        self.assertEqual(r.status_code, 402)
        self.assertEqual(r.json()["code"], "insufficient_credits")
        self.assertEqual(Conversation.objects.count(), 0)

    def test_rate_limit(self):
        with override_settings(BILLING={**__import__("django.conf").conf.settings.BILLING, "MAX_MESSAGES_PER_MINUTE": 2}):
            codes = [self.c.post("/api/chat/", {"message": "Halo", "language": "tet"}, format="json").status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    def test_redeem_endpoint(self):
        pkg = Package.objects.create(name="P", price_usd=1, credits=500)
        code = services.generate_vouchers(pkg, 1)[0]
        r = self.c.post("/api/redeem/", {"code": code}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["balance"], 600)
        self.assertEqual(self.c.post("/api/redeem/", {"code": code}, format="json").status_code, 400)
        self.assertEqual(self.c.get("/api/wallet/").json()["balance"], 600)


class FakeMessages:
    def __init__(self, resp=None, exc=None):
        self.resp, self.exc, self.calls = resp, exc, []

    def create(self, **kw):
        self.calls.append(kw)
        if self.exc:
            raise self.exc
        return self.resp


def fake_resp(text="Bondia!", stop="end_turn", tin=1200, tout=300):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)] if text else [],
        stop_reason=stop,
        usage=SimpleNamespace(input_tokens=tin, output_tokens=tout, cache_creation_input_tokens=0, cache_read_input_tokens=0),
    )


ANTH = {"LLM_BACKEND": "anthropic", "ANTHROPIC_API_KEY": "sk-test", "ANTHROPIC_MODEL": "claude-opus-5-5",
        "ANTHROPIC_EFFORT": "low", "ANTHROPIC_MAX_TOKENS": 2048}


class AnthropicBackendTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("seed_phrases", verbosity=0)
        self.user = make_user()
        self.c = APIClient()
        self.c.force_authenticate(self.user)

    def _settings(self):
        return override_settings(LAFEX_AI={**__import__("django.conf").conf.settings.LAFEX_AI, **ANTH})

    def test_request_shape_and_billing(self):
        fake = SimpleNamespace(messages=FakeMessages(fake_resp()))
        with self._settings():
            llm._client = fake
            r = self.c.post("/api/chat/", {"message": "Bondia", "language": "tet"}, format="json")
        llm._client = None
        self.assertEqual(r.status_code, 200, r.content)
        call = fake.messages.calls[0]
        self.assertEqual(call["model"], "claude-opus-5-5")
        self.assertEqual(call["output_config"], {"effort": "low"})
        self.assertEqual(call["messages"][-1]["role"], "user")
        self.assertIn("LAFEX-AI", call["system"])
        self.assertEqual(r.json()["reply"]["content"], "Bondia!")
        self.assertEqual(r.json()["credits_charged"], services.cost_in_credits(1200, 300))   # 66 poin
        self.assertEqual(CreditTransaction.objects.filter(kind="usage").first().output_tokens, 300)

    def test_failure_is_not_charged(self):
        import anthropic

        err = anthropic.APIConnectionError(request=SimpleNamespace())
        fake = SimpleNamespace(messages=FakeMessages(exc=err))
        with self._settings():
            llm._client = fake
            r = self.c.post("/api/chat/", {"message": "Bondia", "language": "tet"}, format="json")
        llm._client = None
        self.assertEqual(r.status_code, 503)
        self.assertEqual(services.get_wallet(self.user).balance, 100)
        self.assertEqual(Conversation.objects.count(), 0)
        self.assertFalse(CreditTransaction.objects.filter(kind="usage").exists())

    def test_refusal_and_empty(self):
        with self._settings():
            llm._client = SimpleNamespace(messages=FakeMessages(fake_resp(text="", stop="refusal")))
            self.assertEqual(llm.generate_full([{"role": "user", "content": "x"}]).text, prompts.REFUSAL)
            llm._client = SimpleNamespace(messages=FakeMessages(fake_resp(text="", stop="max_tokens")))
            self.assertEqual(llm.generate_full([{"role": "user", "content": "x"}]).text, prompts.EMPTY_ANSWER)
        llm._client = None

    def test_missing_key(self):
        with override_settings(LAFEX_AI={**__import__("django.conf").conf.settings.LAFEX_AI, **ANTH, "ANTHROPIC_API_KEY": ""}):
            with self.assertRaises(llm.LLMUnavailable):
                llm.generate_full([{"role": "user", "content": "x"}])


class AuthPagesTests(TestCase):
    def test_login_and_signup_pages(self):
        for url in ("/accounts/login/", "/accounts/signup/"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertNotContains(r, "Facebook")   # tombol disembunyikan bila kunci belum diisi

    def test_facebook_button_when_configured(self):
        from django.conf import settings

        prov = {"facebook": {**settings.SOCIALACCOUNT_PROVIDERS["facebook"], "APP": {"client_id": "123", "secret": "abc", "key": ""}}}
        with override_settings(FACEBOOK_ENABLED=True, SOCIALACCOUNT_PROVIDERS=prov):
            r = self.client.get("/accounts/login/")
        self.assertContains(r, "Lanjut dengan Facebook")
        self.assertContains(r, "/accounts/facebook/login/")

    def test_email_signup_requires_verification(self):
        r = self.client.post("/accounts/signup/", {"email": "baru@example.com", "password1": "Sandi-Kuat-123", "password2": "Sandi-Kuat-123"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("baru@example.com", mail.outbox[0].to)
        r = self.client.post("/accounts/login/", {"login": "baru@example.com", "password": "Sandi-Kuat-123"})
        self.assertNotEqual(self.client.get("/").status_code, 200)   # belum verifikasi -> belum bisa masuk

    def test_chat_page_requires_login(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])
