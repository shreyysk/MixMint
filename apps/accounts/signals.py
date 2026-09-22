from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile, DJProfile
from apps.commerce.models import DJWallet

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile, _ = Profile.objects.get_or_create(
            user=instance,
            defaults={
                "full_name": (
                    (instance.first_name + " " + instance.last_name).strip() if instance.first_name else instance.email
                ),
                "role": "admin" if instance.is_superuser else "user",
            },
        )
        if instance.is_superuser and profile.role != "admin":
            profile.role = "admin"
            profile.save()


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()


@receiver(post_save, sender=DJProfile)
def create_dj_wallet(sender, instance, created, **kwargs):
    if created:
        DJWallet.objects.get_or_create(dj=instance)
