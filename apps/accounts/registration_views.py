from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from .serializers import UserRegistrationSerializer


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/accounts/register/
    Body: { email, password, full_name }
    Returns: { access, refresh, user_id, role }
    """

    permission_classes = [AllowAny]
    throttle_scope = "auth"
    serializer_class = UserRegistrationSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Send welcome email (async)
        from apps.accounts.tasks import send_welcome_email

        try:
            send_welcome_email.delay(user.id)  # Celery task
        except Exception:
            # Fallback to synchronous/fail silently in case of Celery broker issues during testing/dev
            pass

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user_id": str(user.id),
                "role": user.profile.role,
            },
            status=status.HTTP_201_CREATED,
        )
