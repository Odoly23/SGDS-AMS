from django.core.management.base import BaseCommand

from rag.models import Document
from rag.services import process_document


class Command(BaseCommand):
    help = "Indeks ulang semua dokumen RAG (jalankan setelah mengganti EMBEDDING_BACKEND)."

    def handle(self, *args, **opts):
        for doc in Document.objects.all():
            n = process_document(doc)
            self.stdout.write(f"{doc.title}: {n} potongan ({doc.status})")
