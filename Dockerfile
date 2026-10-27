# MixMint on Railway (web service and the hourly cron service use this same image).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# ffmpeg: promo videos can be rendered right here later instead of on GitHub Actions
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# static files are built into the image (WhiteNoise serves them); a throwaway key is enough here
RUN SECRET_KEY=build-only DEBUG=False ENVIRONMENT=build python manage.py collectstatic --noinput

# 320 s timeout: the Telegram vault and promo posting run up to 300 s in one request (same as Vercel)
CMD gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} \
    --worker-class gthread --threads 4 --timeout 320 --keep-alive 5 --access-logfile - --error-logfile -
