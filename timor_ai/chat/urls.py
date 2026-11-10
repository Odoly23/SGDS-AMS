from django.urls import path

from . import views

urlpatterns = [
    path("", views.chat_page, name="chat-page"),
    path("api/languages/", views.LanguageListView.as_view(), name="api-languages"),
    path("api/conversations/", views.ConversationList.as_view(), name="api-conversations"),
    path("api/conversations/<int:pk>/", views.ConversationDetail.as_view(), name="api-conversation"),
    path("api/chat/", views.ChatView.as_view(), name="api-chat"),
    path("api/detect/", views.DetectView.as_view(), name="api-detect"),
]
