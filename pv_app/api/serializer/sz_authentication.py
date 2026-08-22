from rest_framework import serializers

class UserRegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, write_only=True)
    

class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    # user_type = serializers.ChoiceField(choices=['user', 'admin'], default='user')


class UpdateUserProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    mobile = serializers.CharField(max_length=20, required=False)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=["Male", "Female", "Other"], required=False, allow_null=True)
    profile_image = serializers.ImageField(required=False)

