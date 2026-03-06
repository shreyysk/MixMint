"""
MixMint Collaboration Invite API [Spec P2 §4].

Allows a DJ to invite up to 2 other MixMint DJs as collaborators on a track.
Revenue percentages must be defined at invite time.
Total must equal 100% before the track goes live.
"""

from decimal import Decimal

from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.tracks.models import Track, TrackCollaborator
from apps.accounts.models import DJProfile


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_collaborator(request, track_id):
    """
    Invite another MixMint DJ as a collaborator on a track [Spec P2 §4].

    POST body:
    {
        "collab_dj_slug": "djname",
        "revenue_percentage": 25.00
    }

    Rules:
    - Only the track owner can invite collaborators
    - Max 3 collaborators total (including owner's percentage)
    - Cannot invite yourself
    - Total percentages must sum to exactly 100.00 before track activates
    """
    profile = request.user.profile

    # Must be a DJ
    if profile.role != 'dj':
        return Response({'error': 'Only DJs can invite collaborators.'}, status=status.HTTP_403_FORBIDDEN)

    # Get track owned by this DJ
    try:
        dj_profile = profile.dj_profile
        track = Track.objects.get(id=track_id, dj=dj_profile, is_deleted=False)
    except DJProfile.DoesNotExist:
        return Response({'error': 'DJ profile not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Track.DoesNotExist:
        return Response({'error': 'Track not found or not owned by you.'}, status=status.HTTP_404_NOT_FOUND)

    # Get the collaborator DJ
    collab_slug = request.data.get('collab_dj_slug', '').strip()
    revenue_pct = request.data.get('revenue_percentage')

    if not collab_slug:
        return Response({'error': 'collab_dj_slug is required.'}, status=status.HTTP_400_BAD_REQUEST)

    if revenue_pct is None:
        return Response({'error': 'revenue_percentage is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        revenue_pct = Decimal(str(revenue_pct))
    except Exception:
        return Response({'error': 'revenue_percentage must be a valid number.'}, status=status.HTTP_400_BAD_REQUEST)

    if revenue_pct <= 0 or revenue_pct >= Decimal('100'):
        return Response(
            {'error': 'revenue_percentage must be between 1 and 99.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        collab_dj = DJProfile.objects.get(slug=collab_slug, status='approved')
    except DJProfile.DoesNotExist:
        return Response(
            {'error': f'No approved DJ found with slug "{collab_slug}".'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Cannot invite yourself
    if collab_dj == dj_profile:
        return Response({'error': 'You cannot invite yourself as a collaborator.'}, status=status.HTTP_400_BAD_REQUEST)

    # Max 3 collaborators [Spec P2 §4]
    existing_count = TrackCollaborator.objects.filter(track=track).count()
    if existing_count >= 3:
        return Response(
            {'error': 'Maximum 3 collaborators per track.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if already a collaborator
    if TrackCollaborator.objects.filter(track=track, dj=collab_dj).exists():
        return Response(
            {'error': f'{collab_dj.dj_name} is already a collaborator on this track.'},
            status=status.HTTP_409_CONFLICT
        )

    # Check total doesn't exceed 100
    current_total = TrackCollaborator.objects.filter(track=track).aggregate(
        total=Sum('revenue_percentage')
    )['total'] or Decimal('0')

    if current_total + revenue_pct > Decimal('100'):
        remaining = Decimal('100') - current_total
        return Response(
            {
                'error': f'Total revenue percentage would exceed 100%. You can allocate at most {remaining}% more.',
                'current_total': str(current_total),
                'remaining_available': str(remaining),
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create collaborator record
    TrackCollaborator.objects.create(
        track=track,
        dj=collab_dj,
        revenue_percentage=revenue_pct,
    )

    # Recalculate total after adding
    new_total = TrackCollaborator.objects.filter(track=track).aggregate(
        total=Sum('revenue_percentage')
    )['total'] or Decimal('0')

    return Response({
        'status': 'collaborator_added',
        'collaborator': {
            'dj_name': collab_dj.dj_name,
            'slug': collab_dj.slug,
            'revenue_percentage': str(revenue_pct),
        },
        'total_allocated': str(new_total),
        'remaining': str(Decimal('100') - new_total),
        'ready_to_publish': new_total == Decimal('100'),
        'warning': None if new_total == Decimal('100') else
            f'Revenue split must total 100% before track goes live. Currently: {new_total}%',
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_collaborator(request, track_id, collab_dj_id):
    """Remove a collaborator from a track [Spec P2 §4]."""
    profile = request.user.profile

    try:
        dj_profile = profile.dj_profile
        track = Track.objects.get(id=track_id, dj=dj_profile, is_deleted=False)
    except (DJProfile.DoesNotExist, Track.DoesNotExist):
        return Response({'error': 'Track not found or not owned by you.'}, status=status.HTTP_404_NOT_FOUND)

    deleted, _ = TrackCollaborator.objects.filter(track=track, dj_id=collab_dj_id).delete()

    if deleted == 0:
        return Response({'error': 'Collaborator not found on this track.'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'status': 'collaborator_removed', 'track_id': track_id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_collaborators(request, track_id):
    """List all collaborators and revenue split for a track [Spec P2 §4]."""
    profile = request.user.profile

    try:
        dj_profile = profile.dj_profile
        track = Track.objects.get(id=track_id, dj=dj_profile, is_deleted=False)
    except (DJProfile.DoesNotExist, Track.DoesNotExist):
        return Response({'error': 'Track not found or not owned by you.'}, status=status.HTTP_404_NOT_FOUND)

    collabs = TrackCollaborator.objects.filter(track=track).select_related('dj')
    total = sum(c.revenue_percentage for c in collabs)

    return Response({
        'track_id': track_id,
        'track_title': track.title,
        'collaborators': [{
            'dj_name': c.dj.dj_name,
            'slug': c.dj.slug,
            'dj_id': c.dj.id,
            'revenue_percentage': str(c.revenue_percentage),
        } for c in collabs],
        'total_allocated': str(total),
        'remaining': str(Decimal('100') - total),
        'ready_to_publish': total == Decimal('100'),
    })
