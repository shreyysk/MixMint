web: gunicorn config.wsgi:application --workers 2 --threads 2 --timeout 60 --bind 0.0.0.0:$PORT
worker: celery -A config worker -l info
beat: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
