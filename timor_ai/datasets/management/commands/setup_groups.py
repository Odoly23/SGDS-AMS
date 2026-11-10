"""
Membuat 2 grup untuk crowdsourcing:
  Kontributor -> boleh menambah/mengubah Phrase & Translation (hasilnya DRAFT)
  Reviewer    -> sama + boleh memverifikasi (izin verify_translation) + upload dokumen RAG
Setelah itu: Admin > Users > pilih user > centang "staff status" > masukkan ke grup.
"""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


def perms(*codenames):
    return list(Permission.objects.filter(codename__in=codenames))


class Command(BaseCommand):
    help = "Buat grup Kontributor dan Reviewer."

    def handle(self, *args, **opts):
        contrib, _ = Group.objects.get_or_create(name="Kontributor")
        contrib.permissions.set(perms(
            "add_phrase", "change_phrase", "view_phrase",
            "add_translation", "change_translation", "view_translation", "view_language",
        ))
        reviewer, _ = Group.objects.get_or_create(name="Reviewer")
        reviewer.permissions.set(perms(
            "add_phrase", "change_phrase", "view_phrase",
            "add_translation", "change_translation", "view_translation", "view_language",
            "verify_translation", "add_document", "change_document", "view_document", "view_conversation", "view_message",
        ))
        self.stdout.write(self.style.SUCCESS("Grup Kontributor & Reviewer siap."))
