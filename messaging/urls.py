from django.urls import path
from .views import chat_list_page, chat_page

urlpatterns = [
    path('', chat_list_page),
    path('<str:signed_phone>/', chat_page),

]