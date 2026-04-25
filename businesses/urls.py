from django.urls import path
from .views import (
    faq_page,
    documents_page,
    DocumentUploadView,
    DocumentListView,
    DocumentDeleteView,
)

urlpatterns = [
    # business routes will go here
    path('faq', faq_page, name='faq'),
    path('documents', documents_page, name='documents'),
    path('documents/upload/', DocumentUploadView.as_view(), name='document-upload'),
]
