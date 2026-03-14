from celery import shared_task
from .utils import process_album_zip

@shared_task
def process_album_task(album_id):
    """Asynchronous album ZIP processing [Spec §5]."""
    return process_album_zip(album_id)
