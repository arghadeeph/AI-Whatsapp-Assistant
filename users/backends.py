from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from businesses.models import Business


class EmailOrPhoneBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = None

        # Try login by email
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            pass

        # Try login by business phone number
        if user is None:
            try:
                business = Business.objects.get(phone_number=username)
                # Get the owner of this business
                user_business = business.userbusiness_set.filter(role='owner').first()
                if user_business:
                    user = user_business.user
            except Business.DoesNotExist:
                return None

        # Verify password
        if user and user.check_password(password):
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None