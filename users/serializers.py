from rest_framework import serializers
from django.contrib.auth.models import User
from businesses.models import Business
from .models import UserBusiness


class RegisterSerializer(serializers.Serializer):
    # User fields
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    # Business fields (phone belongs to the business)
    business_name = serializers.CharField()
    business_phone = serializers.CharField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_business_phone(self, value):
        if Business.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A business with this phone already exists.")
        return value

    def create(self, validated_data):
        # Create User — email is the username
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        # Create Business
        business = Business.objects.create(
            name=validated_data['business_name'],
            phone_number=validated_data['business_phone'],
        )
        # Link User → Business as Owner
        UserBusiness.objects.create(user=user, business=business, role='owner')

        return user, business