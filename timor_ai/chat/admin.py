from django.contrib import admin

from .models import Conversation, Language, Message


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "kind", "iso_639_3", "verification", "is_active", "sort_order")
    list_filter = ("kind", "verification", "is_active")
    search_fields = ("name", "native_name", "code")
    list_editable = ("is_active", "sort_order")


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False
    readonly_fields = ("role", "content", "detected_language", "sources", "model_name", "latency_ms", "input_tokens", "output_tokens", "credits_charged", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Melihat log percakapan (hanya baca)."""
    list_display = ("id", "user", "title", "mode", "language", "updated_at", "jumlah_pesan")
    list_filter = ("mode", "language", "created_at")
    search_fields = ("title", "user__username", "messages__content")
    readonly_fields = ("user", "title", "mode", "language", "source_language", "created_at", "updated_at")
    inlines = [MessageInline]

    @admin.display(description="Pesan")
    def jumlah_pesan(self, obj):
        return obj.messages.count()

    def has_add_permission(self, request):
        return False


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "short_content", "detected_language", "credits_charged", "latency_ms", "created_at")
    list_filter = ("role", "detected_language", "created_at")
    search_fields = ("content",)
    readonly_fields = [f.name for f in Message._meta.fields]

    @admin.display(description="Isi")
    def short_content(self, obj):
        return obj.content[:80]

    def has_add_permission(self, request):
        return False
