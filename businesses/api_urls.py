from django.urls import path
from .views import FAQListAPI, FAQDetailAPI, FAQToggleStatusAPI

urlpatterns = [

    path('faq/', FAQListAPI.as_view()),
   
    # Retrieve, Update, Delete
    path('faq/<int:pk>/', FAQDetailAPI.as_view(), name='api-faq-detail'),

    # Toggle Active/Inactive Status
    path('faq/<int:pk>/toggle/', FAQToggleStatusAPI.as_view(), name='api-faq-toggle'),
]