from django.urls import path
from .views import (
    FAQListAPI,
    FAQDetailAPI,
    FAQToggleStatusAPI,
    DocumentUploadView,
    DocumentListView,
    DocumentDeleteView,
)

urlpatterns = [

    path('faq/', FAQListAPI.as_view()),
   
    # Retrieve, Update, Delete
    path('faq/<int:pk>/', FAQDetailAPI.as_view(), name='api-faq-detail'),

    # Toggle Active/Inactive Status
    path('faq/<int:pk>/toggle/', FAQToggleStatusAPI.as_view(), name='api-faq-toggle'),

    path('documents/', DocumentListView.as_view(), name='api-document-list'),
    path('documents/upload/', DocumentUploadView.as_view(), name='api-document-upload'),
    path('documents/<uuid:document_id>/', DocumentDeleteView.as_view(), name='api-document-delete'),
]
