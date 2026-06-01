web: gunicorn config.wsgi:application --workers 4 --worker-class gthread --threads 2 --bind 0.0.0.0:$PORT --timeout 120 --keep-alive 5 --access-logfile - --error-logfile -
worker: celery -A config worker --loglevel=info --concurrency 4
beat: celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
