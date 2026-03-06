from rest_framework import serializers
from .models import User, Profile, DJProfile
from .email_blocklist import validate_email_domain


class UserSerializer(serializers.ModelSerializer):
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
