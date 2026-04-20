from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import login_page, register_page

urlpatterns = [

    # Html pages
    path('login/', login_page, name='login_page'),
    path('register/', register_page, name='register_page'),
]