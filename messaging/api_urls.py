from django.urls import path
from .views import ConversationListAPI, MessagesAPI, SendMessageAPI, AIReplyToggleAPI, MarkConversationReadAPI

urlpatterns = [
    path('conversations/', ConversationListAPI.as_view()),
    path('send-message/', SendMessageAPI.as_view()),
    path('chat/<str:signed_phone>/', MessagesAPI.as_view()),
    path('ai-reply-toggle/', AIReplyToggleAPI.as_view()),
    path('mark-read/', MarkConversationReadAPI.as_view()),
   
]
