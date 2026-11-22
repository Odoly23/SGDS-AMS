"""
Logika crowdsourcing bahasa daerah (dipakai halaman user dan Admin).

Alur kualitas:
  user menulis terjemahan (DRAFT)  ->  user lain memberi suara "benar"
  -> 3 suara setuju => naik ke antrean REVIEW  ->  reviewer (penutur asli/ahli) memverifikasi => VERIFIED
Hanya VERIFIED yang dipakai untuk melatih model. Hadiah poin dibayar saat VERIFIED, sekali saja.
Suara komunitas TIDAK pernah memverifikasi sendiri (mencegah akun palsu mengisi data sampah).
"""
import re

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from billing import services as billing
from chat.models import Language

from .models import Phrase, Translation, Vote

S = Translation.Status
SOURCE_ORDER = ["tet", "ind", "por", "eng"]    # bahasa yang biasanya sudah dikuasai pengisi


class ContribError(Exception):
    """Pesan aman ditampilkan ke user."""


def _norm(text):
    return re.sub(r"\s+", " ", text.strip().lower())


def _language(code, exclude_none=False):
    lang = Language.objects.filter(code=code, is_active=True).first()
    if not lang:
        raise ContribError("Bahasa tidak dikenal.")
    return lang


def _sources(phrase, target_code):
    """Teks sumber dari bahasa lain untuk satu kalimat (terverifikasi didahulukan)."""
    rows = {}
    qs = phrase.translations.exclude(status=S.REJECTED).exclude(language__code=target_code).select_related("language")
    for t in qs:
        cur = rows.get(t.language.code)
        if cur is None or (t.status == S.VERIFIED and cur["status"] != S.VERIFIED):
            rows[t.language.code] = {"lang": t.language.code, "name": t.language.name, "text": t.text, "status": t.status}
    order = {c: i for i, c in enumerate(SOURCE_ORDER)}
    return sorted(rows.values(), key=lambda r: order.get(r["lang"], 99))


# ------------------------------------------------------------ menerjemahkan
def next_task(user, lang_code):
    lang = _language(lang_code)
    mine = Translation.objects.filter(language=lang, contributor=user).values("phrase_id")
    have = Translation.objects.filter(language=lang).exclude(status=S.REJECTED).values("phrase_id")
    todo = Phrase.objects.exclude(id__in=mine)
    phrase = todo.exclude(id__in=have).order_by("?").first() or todo.order_by("?").first()
    if not phrase:
        return None
    sources = _sources(phrase, lang_code)
    if not sources:
        return None
    return {"phrase": phrase.code, "category": phrase.get_category_display(), "context": phrase.context_note, "sources": sources}


def submit(user, phrase_code, lang_code, text, dialect="", notes=""):
    lang = _language(lang_code)
    text = (text or "").strip()
    if not 1 <= len(text) <= 500:
        raise ContribError("Terjemahan harus 1-500 karakter.")
    phrase = Phrase.objects.filter(code=phrase_code).first()
    if not phrase:
        raise ContribError("Kalimat tidak ditemukan.")
    today = timezone.localdate()
    sent = Translation.objects.filter(contributor=user, created_at__date=today).count()
    if sent >= settings.CONTRIB["MAX_SUBMISSIONS_PER_DAY"]:
        raise ContribError("Batas kiriman hari ini tercapai. Terima kasih, lanjutkan besok!")
    norm = _norm(text)
    if any(_norm(t) == norm for t in phrase.translations.filter(language=lang).exclude(status=S.REJECTED).values_list("text", flat=True)):
        raise ContribError("Terjemahan yang sama sudah ada. Periksa di tab 'Periksa' dan beri suara.")
    return Translation.objects.create(
        phrase=phrase, language=lang, text=text, dialect=(dialect or "")[:80].strip(), notes=(notes or "")[:500].strip(),
        status=S.DRAFT, source="komunitas", contributor=user,
    )


# ----------------------------------------------------------------- memeriksa
def next_review(user, lang_code):
    lang = _language(lang_code)
    t = (
        Translation.objects.filter(language=lang, status__in=[S.DRAFT, S.REVIEW])
        .exclude(contributor=user).exclude(votes__user=user)
        .annotate(n=Count("votes")).order_by("n", "?").select_related("phrase").first()
    )
    if not t:
        return None
    return {
        "translation": t.pk, "language": lang.code, "language_name": lang.name, "text": t.text, "dialect": t.dialect,
        "ai_draft": t.source.startswith("seed"), "category": t.phrase.get_category_display(),
        "sources": _sources(t.phrase, lang.code),
    }


def vote(user, translation_id, agree):
    t = Translation.objects.filter(pk=translation_id, status__in=[S.DRAFT, S.REVIEW]).first()
    if not t:
        raise ContribError("Terjemahan tidak tersedia untuk diperiksa.")
    if t.contributor_id == user.pk:
        raise ContribError("Anda tidak bisa memeriksa terjemahan sendiri.")
    if Vote.objects.filter(user=user, created_at__date=timezone.localdate()).count() >= settings.CONTRIB["MAX_VOTES_PER_DAY"]:
        raise ContribError("Batas pemeriksaan hari ini tercapai.")
    with transaction.atomic():
        _, created = Vote.objects.get_or_create(translation=t, user=user, defaults={"agree": bool(agree)})
        if not created:
            raise ContribError("Anda sudah memberi suara untuk terjemahan ini.")
        yes = t.votes.filter(agree=True).count()
        no = t.votes.filter(agree=False).count()
        if t.status == S.DRAFT and yes >= settings.CONTRIB["VOTES_TO_REVIEW"] and yes >= 2 * no:
            t.status = S.REVIEW      # naik ke antrean reviewer; BELUM terverifikasi
            t.save(update_fields=["status", "updated_at"])
    return {"yes": yes, "no": no, "status": t.status}


# ------------------------------------------------------- keputusan reviewer
def set_status(translation, new_status, reviewer):
    """Ubah status oleh reviewer. Membayar hadiah sekali saja saat pertama kali VERIFIED."""
    with transaction.atomic():
        t = Translation.objects.select_for_update().get(pk=translation.pk)
        t.status = new_status
        if new_status in (S.VERIFIED, S.REJECTED):
            t.reviewed_by = reviewer
        if new_status == S.VERIFIED and not t.rewarded:
            t.rewarded = True
            cfg = settings.CONTRIB
            if t.contributor_id and t.contributor_id != getattr(reviewer, "pk", None):   # reviewer tak boleh memberi hadiah pada diri sendiri
                billing.grant_reward(t.contributor, cfg["REWARD_VERIFIED"], f"Terjemahan {t.language.name} terverifikasi")
            for v in t.votes.filter(agree=True).exclude(user_id=t.contributor_id).select_related("user"):
                billing.grant_reward(v.user, cfg["REWARD_VOTE"], f"Pemeriksaan {t.language.name} tepat")
        t.save()
    return t


# ----------------------------------------------------------- statistik
def my_stats(user):
    from billing.models import CreditTransaction

    mine = Translation.objects.filter(contributor=user)
    earned = sum(CreditTransaction.objects.filter(wallet__user=user, kind="reward").values_list("amount", flat=True))
    return {
        "submitted": mine.count(),
        "verified": mine.filter(status=S.VERIFIED).count(),
        "pending": mine.filter(status__in=[S.DRAFT, S.REVIEW]).count(),
        "votes": Vote.objects.filter(user=user).count(),
        "points_earned": earned,
    }


def leaderboard(user, limit=10):
    rows = (
        Translation.objects.filter(status=S.VERIFIED, contributor__isnull=False)
        .values("contributor").annotate(n=Count("id")).order_by("-n")[:limit]
    )
    # nama samaran: tidak menampilkan email/nama asli
    return [{"rank": i + 1, "name": f"Kontributor #{r['contributor']}", "verified": r["n"], "me": r["contributor"] == user.pk}
            for i, r in enumerate(rows)]
