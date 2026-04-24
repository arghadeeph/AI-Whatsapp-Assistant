"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView


urlpatterns = [

    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),

    path('admin/', admin.site.urls),
    
    path('auth/', include('users.urls')),        # HTML: /auth/login/, /auth/register/
    path('api/auth/', include('users.api_urls')),    # API: /api/auth/login/, /api/auth/register/
   
    path('api/dashboard/', include('dashboard.api_urls')),
    path('dashboard/', include('dashboard.urls')),

    path('api/whatsapp/', include('whatsapp.urls')),

    path('chat/', include('messaging.urls')),
    path('api/messages/', include('messaging.api_urls')),

    path('business/', include('businesses.urls')),
    path('api/business/', include('businesses.api_urls')),
]
