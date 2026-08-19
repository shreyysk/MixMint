# MixMint 2.0 — Railway Deployment Guide

## Architecture
- **Web**: Gunicorn (4 workers, gthread, 2 threads each)
- **Worker**: Celery worker (4 concurrency)
- **Beat**: Celery beat with django-celery-beat (DatabaseScheduler)
- **Database**: PostgreSQL (Railway managed)
- **Cache/Queue**: Redis (Railway managed)
- **Storage**: Cloudflare R2 (external)
- **Payments**: PhonePe (primary) + Razorpay (fallback)
- **Email**: Resend

---

## One-Time Setup (Railway Dashboard)

1. **Create New Project** → "Deploy from GitHub repo"
2. **Add Services**:
   - PostgreSQL → note `DATABASE_URL`
   - Redis → note `REDIS_URL`
3. **Set Environment Variables** (see below)
4. **Deploy** — Railway auto-detects `Procfile`

---

## Environment Variables

```bash
# Django Core
SECRET_KEY=<generate: openssl rand -base64 50>
DEBUG=False
ALLOWED_HOSTS=<your-domain>.railway.app,mixmint.site
ENVIRONMENT=production
BASE_URL=https://<your-domain>.railway.app
ADMIN_URL=admin/                    # or custom path for obscurity

# Database (auto-injected by Railway PostgreSQL)
DATABASE_URL=postgres://...

# Redis (auto-injected by Railway Redis)
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...

# Storage (Cloudflare R2)
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_ENDPOINT=https://<account>.r2.cloudflarestorage.com
R2_BUCKET_NAME=mixmint-files
R2_PUBLIC_URL=https://pub-<bucket>.r2.dev

# Payments — PhonePe (Primary)
DEFAULT_PAYMENT_GATEWAY=phonepe
PHONEPE_MERCHANT_ID=...
PHONEPE_SALT_KEY=...
PHONEPE_SALT_INDEX=1

# Payments — Razorpay (Fallback)
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...

# Email (Resend)
RESEND_API_KEY=re_...
FROM_EMAIL=noreply@mixmint.site

# Admin
ADMIN_EMAIL=admin@mixmint.site
CRON_SECRET=<generate: openssl rand -hex 32>

# Google OAuth (optional)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

---

## Post-Deploy Commands (Run Once)

```bash
# 1. Run migrations
railway run python manage.py migrate

# 2. Create superuser
railway run python manage.py createsuperuser

# 3. Collect static files
railway run python manage.py collectstatic --noinput

# 4. Verify periodic tasks exist in django-celery-beat
railway run python -c "
from django_celery_beat.models import PeriodicTask
for t in PeriodicTask.objects.all():
    print(t.name, t.crontab)
"
```

Expected periodic tasks:
- Process Pro renewals and storage overage (daily 02:00 UTC)
- Cleanup expired download tokens (daily 03:00 UTC)
- Update weekly sales for tracks (daily 04:00 UTC)
- Detect offload candidates (weekly Monday 05:00 UTC)

---

## Background Jobs

| Job | Trigger | Description |
|-----|---------|-------------|
| `payout_cron` | Daily 02:00 UTC | Pro renewals, storage overage billing |
| `cleanup_tokens` | Daily 03:00 UTC | Delete expired download tokens |
| `update_weekly_sales` | Daily 04:00 UTC | Recalculate `sales_last_7_days` on tracks |
| `detect_offload_candidates` | Weekly Mon 05:00 UTC | Find underperforming/free tracks for offload |

All jobs run via **Celery beat → Celery worker** (persistent processes managed by Procfile).

---

## Health Checks

```bash
# Web health
curl https://<domain>.railway.app/health/

# Worker status
railway run python -c "
from celery import Celery
app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
inspect = app.control.inspect()
print('Active:', inspect.active())
print('Registered:', inspect.registered())
"

# Beat schedule
railway run python -c "
from django_celery_beat.models import PeriodicTask
for t in PeriodicTask.objects.filter(enabled=True):
    print(f'{t.name}: {t.crontab}')
"
```

---

## Rollback

```bash
railway rollback <deployment-id>
```

---

## Custom Domain

1. Settings → Domains → Add `mixmint.site`
2. Configure DNS per Railway instructions
3. Update `ALLOWED_HOSTS` and `BASE_URL`
4. Redeploy