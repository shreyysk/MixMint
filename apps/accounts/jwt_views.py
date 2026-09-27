"""JWT login / refresh / logout for API and mobile clients (email + password)."""

from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class MixMintTokenObtainPairSerializer(TokenObtainPairSerializer):
    default_error_messages = {"no_active_account": "Invalid email or password."}

    def validate(self, attrs):
        attrs[self.username_field] = (attrs.get(self.username_field) or "").strip().lower()
        data = super().validate(attrs)
        profile = getattr(self.user, "profile", None)
        if profile is not None and (profile.is_banned or profile.is_frozen):
            raise serializers.ValidationError({"detail": "This account is restricted. Contact support."})
        data["role"] = getattr(profile, "role", "user")
        return data


class LoginView(TokenObtainPairView):
    """POST {email, password} -> {access, refresh, role}"""

    serializer_class = MixMintTokenObtainPairSerializer
    throttle_scope = "auth"


class RefreshView(TokenRefreshView):
    """POST {refresh} -> {access, refresh}"""

    throttle_scope = "auth"


class LogoutView(APIView):
    """POST {refresh} -> 205. Blacklists the refresh token so it can't be reused."""

    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        try:
            RefreshToken(request.data.get("refresh", "")).blacklist()
        except TokenError:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)
