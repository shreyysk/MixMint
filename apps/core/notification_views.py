"""
Push Notification & A/B Testing API Endpoints.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from django.utils import timezone

from apps.accounts.models import (
    PushSubscription, NotificationPreference, InAppNotification,
    Experiment, Variant, UserExperiment, ExperimentEvent
)
from .push_notifications import PushNotificationService
from .ab_testing import ABTestingService


# ============================================
# PUSH NOTIFICATION ENDPOINTS
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_push_subscription(request):
    """Register a push notification subscription."""
    endpoint = request.data.get('endpoint')
    p256dh = request.data.get('p256dh')
    auth = request.data.get('auth')
    device_type = request.data.get('device_type', 'web')
    
    if not all([endpoint, p256dh, auth]):
        return Response({'error': 'Missing subscription data'}, status=400)
    
    sub, created = PushSubscription.objects.update_or_create(
        user=request.user.profile,
        endpoint=endpoint,
        defaults={
            'p256dh_key': p256dh,
            'auth_key': auth,
            'device_type': device_type,
            'is_active': True,
        }
    )
    
    return Response({
        'status': 'subscribed' if created else 'updated',
        'subscription_id': sub.id
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def unregister_push_subscription(request):
    """Unregister a push subscription."""
    endpoint = request.data.get('endpoint')
    
    if endpoint:
        PushSubscription.objects.filter(
            user=request.user.profile,
            endpoint=endpoint
        ).delete()
    else:
        # Unregister all
        PushSubscription.objects.filter(user=request.user.profile).delete()
    
    return Response({'status': 'unsubscribed'})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def notification_preferences(request):
    """Get or update notification preferences."""
    prefs, _ = NotificationPreference.objects.get_or_create(user=request.user.profile)
    
    if request.method == 'PATCH':
        for field in ['email_sales', 'email_payouts', 'email_milestones', 'email_marketing',
                      'push_sales', 'push_new_followers', 'push_milestones', 'push_promotions']:
            if field in request.data:
                setattr(prefs, field, request.data[field])
        prefs.save()
    
    return Response({
        'email': {
            'sales': prefs.email_sales,
            'payouts': prefs.email_payouts,
            'milestones': prefs.email_milestones,
            'marketing': prefs.email_marketing,
        },
        'push': {
            'sales': prefs.push_sales,
            'new_followers': prefs.push_new_followers,
            'milestones': prefs.push_milestones,
            'promotions': prefs.push_promotions,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """Get user's in-app notifications."""
    unread_only = request.query_params.get('unread', 'false').lower() == 'true'
    limit = min(int(request.query_params.get('limit', 20)), 50)
    
    notifications = InAppNotification.objects.filter(user=request.user.profile)
    
    if unread_only:
        notifications = notifications.filter(is_read=False)
    
    notifications = notifications[:limit]
    
    return Response({
        'notifications': [
            {
                'id': n.id,
                'type': n.notification_type,
                'title': n.title,
                'message': n.message,
                'data': n.data,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
            }
            for n in notifications
        ],
        'unread_count': InAppNotification.objects.filter(
            user=request.user.profile, is_read=False
        ).count()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notifications_read(request):
    """Mark notifications as read."""
    notification_ids = request.data.get('ids', [])
    mark_all = request.data.get('all', False)
    
    if mark_all:
        InAppNotification.objects.filter(
            user=request.user.profile, is_read=False
        ).update(is_read=True, read_at=timezone.now())
    elif notification_ids:
        InAppNotification.objects.filter(
            user=request.user.profile, id__in=notification_ids
        ).update(is_read=True, read_at=timezone.now())
    
    return Response({'status': 'ok'})


# ============================================
# A/B TESTING ENDPOINTS
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_experiment_variant(request, experiment_name):
    """Get user's variant for an experiment."""
    result = ABTestingService.get_variant(request.user.profile, experiment_name)
    
    if not result:
        return Response({'in_experiment': False})
    
    return Response({
        'in_experiment': True,
        'variant': result['variant'],
        'config': result['config'],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def track_experiment_event(request, experiment_name):
    """Track an event for an experiment."""
    event_type = request.data.get('event_type')
    value = request.data.get('value')
    metadata = request.data.get('metadata', {})
    
    if not event_type:
        return Response({'error': 'event_type required'}, status=400)
    
    success = ABTestingService.track_event(
        request.user.profile,
        experiment_name,
        event_type,
        value=value,
        metadata=metadata
    )
    
    return Response({'tracked': success})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_experiments(request):
    """Get all experiments a user is part of."""
    from .ab_testing import UserExperiment
    
    assignments = UserExperiment.objects.filter(
        user=request.user.profile
    ).select_related('experiment', 'variant')
    
    return Response({
        'experiments': [
            {
                'name': a.experiment.name,
                'variant': a.variant.name,
                'config': a.variant.config,
                'assigned_at': a.assigned_at.isoformat(),
            }
            for a in assignments
            if a.experiment.is_active()
        ]
    })


# ============================================
# ADMIN ENDPOINTS
# ============================================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_experiment_stats(request, experiment_name):
    """Get experiment statistics (admin only)."""
    stats = ABTestingService.get_experiment_stats(experiment_name)
    
    if not stats:
        return Response({'error': 'Experiment not found'}, status=404)
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_list_experiments(request):
    """List all experiments (admin only)."""
    experiments = Experiment.objects.all().order_by('-created_at')
    
    return Response({
        'experiments': [
            {
                'id': e.id,
                'name': e.name,
                'status': e.status,
                'target': e.target_audience,
                'traffic': e.traffic_percentage,
                'variants': e.variants.count(),
                'is_active': e.is_active(),
            }
            for e in experiments
        ]
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_create_experiment(request):
    """Create a new experiment (admin only)."""
    name = request.data.get('name')
    description = request.data.get('description', '')
    target = request.data.get('target_audience', 'all')
    traffic = request.data.get('traffic_percentage', 100)
    variants_data = request.data.get('variants', [])
    
    if not name:
        return Response({'error': 'name required'}, status=400)
    
    if Experiment.objects.filter(name=name).exists():
        return Response({'error': 'Experiment with this name exists'}, status=400)
    
    experiment = Experiment.objects.create(
        name=name,
        description=description,
        target_audience=target,
        traffic_percentage=traffic,
        status='draft'
    )
    
    # Create variants
    for v_data in variants_data:
        Variant.objects.create(
            experiment=experiment,
            name=v_data.get('name', 'control'),
            weight=v_data.get('weight', 50),
            config=v_data.get('config', {})
        )
    
    return Response({
        'id': experiment.id,
        'name': experiment.name,
        'status': 'created'
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_update_experiment_status(request, experiment_id):
    """Update experiment status (admin only)."""
    status = request.data.get('status')
    
    if status not in ['draft', 'running', 'paused', 'completed']:
        return Response({'error': 'Invalid status'}, status=400)
    
    try:
        experiment = Experiment.objects.get(id=experiment_id)
    except Experiment.DoesNotExist:
        return Response({'error': 'Experiment not found'}, status=404)
    
    experiment.status = status
    if status == 'running' and not experiment.start_date:
        experiment.start_date = timezone.now()
    experiment.save()
    
    return Response({'status': status})
