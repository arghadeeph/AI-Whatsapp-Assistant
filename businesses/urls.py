from django.urls import path
from .views import (
    faq_page,
    DocumentUploadView,
    DocumentListView,
    DocumentDeleteView,
)

urlpatterns = [
    # business routes will go here
    path('faq', faq_page, name='faq'),
    path('documents/', DocumentListView.as_view(), name='document-list'),
    path('documents/upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('documents/<uuid:document_id>/', DocumentDeleteView.as_view(), name='document-delete'),
]
