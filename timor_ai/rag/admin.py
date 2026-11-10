from django.contrib import admin, messages

from .models import Chunk, Document
from .services import process_document


@admin.action(description="Proses / indeks ulang dokumen terpilih")
def reprocess(modeladmin, request, queryset):
    for doc in queryset:
        n = process_document(doc)
        modeladmin.message_user(request, f"{doc.title}: {n} potongan teks.", messages.SUCCESS if n else messages.WARNING)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "language", "status", "jumlah_chunk", "created_at")
    list_filter = ("category", "status", "language")
    search_fields = ("title", "source_note")
    readonly_fields = ("status", "error", "uploaded_by")
    actions = [reprocess]

    @admin.display(description="Potongan")
    def jumlah_chunk(self, obj):
        return obj.chunks.count()

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
        # Otomatis proses saat file baru diunggah / diganti
        if not change or "file" in form.changed_data:
            n = process_document(obj)
            if obj.status == Document.Status.DONE:
                messages.success(request, f"Dokumen diproses: {n} potongan teks diindeks.")
            else:
                messages.error(request, f"Gagal memproses: {obj.error}")


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "index", "preview", "embedding_backend")
    list_filter = ("document",)
    search_fields = ("text",)
    readonly_fields = ("document", "index", "text", "embedding_backend")
    exclude = ("embedding",)

    @admin.display(description="Isi")
    def preview(self, obj):
        return obj.text[:80]

    def has_add_permission(self, request):
        return False
