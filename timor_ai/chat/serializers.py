from rest_framework import serializers

from .models import Conversation, Language, Message


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["code", "name", "native_name", "kind", "verification"]


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "content", "detected_language", "sources", "latency_ms", "credits_charged", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    language = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "title", "mode", "language", "updated_at"]


class ChatRequestSerializer(serializers.Serializer):
    """Memvalidasi data JSON yang dikirim ke POST /api/chat/."""
    message = serializers.CharField(max_length=4000, trim_whitespace=True)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    language = serializers.SlugRelatedField(
        slug_field="code", queryset=Language.objects.filter(is_active=True),
        help_text="Bahasa jawaban (mode chat) / bahasa tujuan (mode translate)",
    )
    mode = serializers.ChoiceField(choices=Conversation.Mode.choices, default=Conversation.Mode.CHAT)
    source_language = serializers.SlugRelatedField(
        slug_field="code", queryset=Language.objects.filter(is_active=True), required=False, allow_null=True,
        help_text="Hanya mode translate. Kosongkan = auto-detect.",
    )
