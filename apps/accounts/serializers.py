from rest_framework import serializers
from .models import User, Profile, DJProfile
from .email_blocklist import validate_email_domain


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="profile.role", read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "role", "date_joined")
        read_only_fields = ("id", "date_joined")

    def validate_email(self, value):
        """Block temporary/disposable email domains [Spec P2 §13]."""
        try:
            validate_email_domain(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        return value


class ProfileSerializer(serializers.ModelSerializer):
    """A user's own profile. Only cosmetic fields are writable — never role/flags/quotas."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = (
            "user",
            "role",
            "full_name",
            "avatar_url",
            "is_verified_dj",
            "is_pro_dj",
            "pro_plan_type",
            "pro_expires_at",
            "storage_quota_mb",
            "store_paused",
            "created_at",
        )
        read_only_fields = tuple(f for f in fields if f not in ("full_name", "avatar_url"))

    def validate_full_name(self, value):
        value = (value or "").strip()
        if not value or len(value) > 120:
            raise serializers.ValidationError("Name must be 1-120 characters.")
        return value

    def validate_avatar_url(self, value):
        if value and not value.lower().startswith("https://"):
            raise serializers.ValidationError("Avatar must be an https:// URL.")
        return value


class PublicDJProfileSerializer(serializers.ModelSerializer):
    """Public storefront data. No payout, bank, PAN, OTP or contact fields."""

    is_pro = serializers.BooleanField(source="profile.is_pro_dj", read_only=True)
    avatar_url = serializers.URLField(source="profile.avatar_url", read_only=True)

    class Meta:
        model = DJProfile
        fields = (
            "id",
            "dj_name",
            "slug",
            "bio",
            "social_links",
            "genres",
            "location",
            "is_verified",
            "is_pro",
            "avatar_url",
            "popularity_score",
            "created_at",
        )
        read_only_fields = fields


# Back-compat name used elsewhere in the codebase.
DJProfileSerializer = PublicDJProfileSerializer


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ("email", "password", "full_name")

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
        email = validated_data["email"]
        password = validated_data["password"]
        full_name = validated_data["full_name"]

        user = User.objects.create_user(email=email, password=password)

        # Profile is created via post_save signal
        profile = user.profile
        profile.full_name = full_name
        profile.save()

        return user
