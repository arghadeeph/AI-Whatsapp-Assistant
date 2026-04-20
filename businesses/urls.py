from django.urls import path
from .views import faq_page

urlpatterns = [
    # business routes will go here
    path('faq', faq_page, name='faq'),
]