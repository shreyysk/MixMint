from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from .models import User, Profile, DJProfile
from .serializers import UserSerializer, ProfileSerializer, DJProfileSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def confirm_age(self, request):
        """Explicit 18+ age confirmation [Spec §3.1]."""
        profile = request.user.profile
        profile.has_confirmed_age = True
        profile.save(update_fields=['has_confirmed_age'])
        return Response({'status': 'confirmed', 'has_confirmed_age': True})

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Profile.objects.all()
        return Profile.objects.filter(user=self.request.user)

class DJProfileViewSet(viewsets.ModelViewSet):
    queryset = DJProfile.objects.all()
    serializer_class = DJProfileSerializer
    lookup_field = 'slug'
    
    def get_queryset(self):
        return DJProfile.objects.filter(status='approved')

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_age(request):
    """Explicit 18+ age confirmation [Spec §3.1]."""
    profile = request.user.profile
    profile.has_confirmed_age = True
    profile.save(update_fields=['has_confirmed_age'])
    return Response({'status': 'confirmed', 'has_confirmed_age': True})
