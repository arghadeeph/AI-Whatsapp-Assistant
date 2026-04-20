from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import RegisterSerializer
from businesses.models import Business
from django.shortcuts import render


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user, business = serializer.save()
            tokens = get_tokens_for_user(user)
            return Response({
                "message": "Registration successful.",
                "name": user.get_full_name(),
                "email": user.email,
                "business": business.name,
                "business_phone": business.phone_number,
                **tokens,  # includes access + refresh tokens
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get('identifier')
        password = request.data.get('password')

        user = authenticate(request, username=identifier, password=password)
        if user:
            tokens = get_tokens_for_user(user)
            user_business = user.userbusiness_set.select_related('business').first()
            return Response({
                "message": "Login successful.",
                "name": user.get_full_name(),
                "email": user.email,
                "business": user_business.business.name if user_business else None,
                "business_phone": user_business.business.phone_number if user_business else None,
                **tokens,
            })
        return Response(
            {"error": "Invalid email/phone or password."},
            status=status.HTTP_401_UNAUTHORIZED
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()  # invalidate the refresh token
            return Response({"message": "Logged out successfully."})
        except Exception:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # businesses = user.userbusiness_set.select_related('business').all()
        business = Business.objects.get(id=request.business_id)
        return Response({

            "name": user.get_full_name(),
            "email": user.email,
            "business": {
                "id": business.id,
                "name": business.name,
                "phone": business.phone_number,
                "ai_enabled": business.ai_enabled,
                "tone": business.tone,
            }
                
        })
    
def login_page(request):
    return render(request, 'auth/login.html', {'show_header': False})

def register_page(request):
    return render(request, 'auth/register.html', {'show_header': False})