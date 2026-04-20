from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .models import Business
from users.models import UserBusiness


class TenantMiddleware:
    """
    Runs on every request.
    - Authenticates the JWT token
    - Finds the user's business
    - Attaches request.business and request.business_id
    - Skips public routes (login, register, admin)
    """

    # These paths skip the middleware completely
    PUBLIC_PATHS = [
        '/api/auth/login/',
        '/api/auth/register/',
        '/api/auth/token/refresh/',
        '/admin/',
        '/auth/login-page/',
        '/auth/register-page/',
        '/api/whatsapp/webhook/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_authenticator = JWTAuthentication()

    def __call__(self, request):
        # Skip middleware for public paths
        if self._is_public(request.path):
            return self.get_response(request)

        # Skip middleware for non-API HTML pages
        # (dashboard, chat etc — those are protected by JS auth guard)
        if not request.path.startswith('/api/'):
            return self.get_response(request)

        # Try to authenticate the JWT token
        try:
            auth_result = self.jwt_authenticator.authenticate(request)

            # No token provided on a protected API route
            if auth_result is None:
                return JsonResponse(
                    {"error": "Authentication required."},
                    status=401
                )

            user, token = auth_result

            # Find the user's business
            user_business = (
                UserBusiness.objects
                .select_related('business')
                .filter(user=user)
                .first()
            )

            if not user_business:
                return JsonResponse(
                    {"error": "No business associated with this account."},
                    status=403
                )

            # Attach to request — available in every view
            request.user = user
            request.business = user_business.business
            request.business_id = user_business.business_id
            request.user_role = user_business.role

        except (InvalidToken, TokenError) as e:
            return JsonResponse(
                {"error": "Invalid or expired token.", "detail": str(e)},
                status=401
            )

        return self.get_response(request)

    def _is_public(self, path):
        return any(path.startswith(public) for public in self.PUBLIC_PATHS)