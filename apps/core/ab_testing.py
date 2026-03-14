"""
MixMint A/B Testing Framework.

Simple but powerful A/B testing for:
- UI variations
- Pricing experiments
- Feature flags
- Conversion optimization
"""

from django.utils import timezone
from django.core.cache import cache
import random
import hashlib


class ABTestingService:
    """Service for managing A/B tests."""
    
    @classmethod
    def get_variant(cls, user_profile, experiment_name):
        """
        Get or assign a variant for a user in an experiment.
        Returns variant name and config, or None if not in experiment.
        """
        from apps.accounts.models import Experiment, UserExperiment
        
        # Check cache first
        cache_key = f"ab_{user_profile.id}_{experiment_name}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Get experiment
        try:
            experiment = Experiment.objects.get(name=experiment_name)
        except Experiment.DoesNotExist:
            return None
        
        if not experiment.is_active():
            return None
        
        # Check targeting
        if not cls._matches_target(user_profile, experiment):
            return None
        
        # Check traffic percentage
        if not cls._in_traffic(user_profile, experiment):
            return None
        
        # Check existing assignment
        assignment = UserExperiment.objects.filter(
            user=user_profile,
            experiment=experiment
        ).select_related('variant').first()
        
        if assignment:
            result = {
                'variant': assignment.variant.name,
                'config': assignment.variant.config
            }
            cache.set(cache_key, result, 3600)
            return result
        
        # Assign new variant
        variant = cls._assign_variant(user_profile, experiment)
        if not variant:
            return None
        
        result = {
            'variant': variant.name,
            'config': variant.config
        }
        cache.set(cache_key, result, 3600)
        return result
    
    @classmethod
    def track_event(cls, user_profile, experiment_name, event_type, value=None, metadata=None):
        """Track an event for a user in an experiment."""
        from apps.accounts.models import UserExperiment, ExperimentEvent
        
        assignment = UserExperiment.objects.filter(
            user=user_profile,
            experiment__name=experiment_name
        ).first()
        
        if not assignment:
            return False
        
        ExperimentEvent.objects.create(
            user_experiment=assignment,
            event_type=event_type,
            value=value,
            metadata=metadata or {}
        )
        return True
    
    @classmethod
    def get_experiment_stats(cls, experiment_name):
        """Get stats for an experiment."""
        from apps.accounts.models import Experiment, UserExperiment, ExperimentEvent
        
        try:
            experiment = Experiment.objects.get(name=experiment_name)
        except Experiment.DoesNotExist:
            return None
        
        stats = {
            'name': experiment.name,
            'status': experiment.status,
            'variants': []
        }
        
        for variant in experiment.variants.all():
            assignments = UserExperiment.objects.filter(
                experiment=experiment,
                variant=variant
            )
            
            events = ExperimentEvent.objects.filter(
                user_experiment__variant=variant,
                user_experiment__experiment=experiment
            )
            
            variant_stats = {
                'name': variant.name,
                'users': assignments.count(),
                'events': {},
            }
            
            # Count events by type
            for event_type in events.values_list('event_type', flat=True).distinct():
                type_events = events.filter(event_type=event_type)
                variant_stats['events'][event_type] = {
                    'count': type_events.count(),
                    'conversion_rate': round(type_events.count() / max(assignments.count(), 1) * 100, 2)
                }
            
            stats['variants'].append(variant_stats)
        
        return stats
    
    @classmethod
    def _matches_target(cls, user_profile, experiment):
        """Check if user matches experiment's target audience."""
        target = experiment.target_audience
        if target == 'all':
            return True
        if target == 'dj' and user_profile.role == 'dj':
            return True
        if target == 'buyer' and user_profile.role == 'buyer':
            return True
        if target == 'new_user':
            days_old = (timezone.now() - user_profile.created_at).days
            return days_old <= 7
        return False
    
    @classmethod
    def _in_traffic(cls, user_profile, experiment):
        """Deterministic check if user is in traffic percentage."""
        hash_input = f"{user_profile.id}_{experiment.id}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = hash_val % 100
        return bucket < experiment.traffic_percentage
    
    @classmethod
    def _assign_variant(cls, user_profile, experiment):
        """Assign a variant to a user based on weights."""
        from apps.accounts.models import UserExperiment
        
        variants = list(experiment.variants.all())
        if not variants:
            return None
        
        # Weighted random selection
        total_weight = sum(v.weight for v in variants)
        rand_val = random.randint(0, total_weight - 1)
        
        cumulative = 0
        selected = variants[0]
        for variant in variants:
            cumulative += variant.weight
            if rand_val < cumulative:
                selected = variant
                break
        
        # Create assignment
        UserExperiment.objects.create(
            user=user_profile,
            experiment=experiment,
            variant=selected
        )
        
        return selected
