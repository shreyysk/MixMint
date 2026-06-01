from rest_framework import serializers
from .models import User, Profile, DJProfile
from .email_blocklist import validate_email_domain


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='profile.role', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'role', 'date_joined')
        read_only_fields = ('id', 'date_joined')

    def validate_email(self, value):
        """Block temporary/disposable email domains [Spec P2 §13]."""
        try:
            validate_email_domain(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        return value


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = '__all__'


class DJProfileSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = DJProfile
        fields = '__all__'


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'full_name')

    def validate_email(self, value):
        """Block temporary/disposable email domains."""
        try:
            validate_email_domain(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        full_name = validated_data['full_name']
        
        user = User.objects.create_user(email=email, password=password)
        
        # Profile is created via post_save signal
        profile = user.profile
        profile.full_name = full_name
        profile.save()
        
        return user

