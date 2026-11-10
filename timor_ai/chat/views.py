"""
View chat.

  chat_page          -> halaman HTML (template)
  LanguageListView   -> GET  /api/languages/
  ConversationList   -> GET  /api/conversations/
  ConversationDetail -> GET  /api/conversations/<id>/   DELETE
  ChatView           -> POST /api/chat/
  DetectView         -> POST /api/detect/
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .detect import detect_language
from .models import Conversation, Language
from .serializers import (
    ChatRequestSerializer,
    ConversationSerializer,
    LanguageSerializer,
    MessageSerializer,
)


@login_required
def chat_page(request):
    return render(request, "chat/chat.html")


class LanguageListView(APIView):
    def get(self, request):
        langs = Language.objects.filter(is_active=True)
        return Response(LanguageSerializer(langs, many=True).data)


class ConversationList(APIView):
    def get(self, request):
        # hanya percakapan milik user yang login
        convs = Conversation.objects.filter(user=request.user)[:50]
        return Response(ConversationSerializer(convs, many=True).data)


class ConversationDetail(APIView):
    def _get(self, request, pk):
        return Conversation.objects.filter(user=request.user, pk=pk).first()

    def get(self, request, pk):
        conv = self._get(request, pk)
        if not conv:
            return Response({"detail": "Tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            "conversation": ConversationSerializer(conv).data,
            "messages": MessageSerializer(conv.messages.all(), many=True).data,
        })

    def delete(self, request, pk):
        conv = self._get(request, pk)
        if not conv:
            return Response({"detail": "Tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DetectView(APIView):
    def post(self, request):
        text = str(request.data.get("text", ""))[:2000]
        code = detect_language(text)
        return Response({"code": code, "name": Language.objects.filter(code=code).values_list("name", flat=True).first()})


class ChatView(APIView):
    """
    Contoh body JSON:
      {"message": "Bondia, oinsá?", "language": "tet", "mode": "chat"}
      {"message": "Selamat pagi", "language": "por", "mode": "translate", "source_language": "ind"}
    """

    def post(self, request):
        ser = ChatRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        conv_id = data.get("conversation_id")
        if conv_id:
            conv = Conversation.objects.filter(user=request.user, pk=conv_id).first()
            if not conv:
                return Response({"detail": "Percakapan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
            # user boleh mengganti bahasa di tengah percakapan
            conv.language = data["language"]
            conv.mode = data["mode"]
            conv.source_language = data.get("source_language")
            conv.save()
        else:
            conv = Conversation.objects.create(
                user=request.user,
                title=data["message"][:60],
                mode=data["mode"],
                language=data["language"],
                source_language=data.get("source_language"),
            )

        if conv.mode == Conversation.Mode.TRANSLATE:
            reply = services.reply_translate(conv, data["message"])
        else:
            reply = services.reply_chat(conv, data["message"])
        conv.save()  # memperbarui updated_at

        return Response({"conversation_id": conv.pk, "reply": MessageSerializer(reply).data})
