from celery import shared_task
from django.core.management import call_command

@shared_task
def cleanup_expired_tokens():
    """Daily task to clean up expired download tokens [BUG-14]."""
    call_command('cleanup_tokens')
    return "Expired tokens cleaned up successfully."
