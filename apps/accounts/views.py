from rest_framework import viewsets, permissions
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
        """Age confirmation is handled implicitly at signup (18+ ToS acceptance)."""
        return Response({'status': 'ok', 'message': 'Age acknowledged via Terms of Service acceptance.'})

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
    """Age confirmation is handled at signup via Terms of Service acceptance."""
    return Response({'status': 'ok', 'message': 'Age acknowledged via Terms of Service acceptance.'})
