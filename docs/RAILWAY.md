# Moving MixMint from Vercel to Railway

## Live setup (created 29 Oct 2026)
Railway project **mixmint** (Hobby plan, region Singapore `asia-southeast1-eqsg3a`):

| Service | Source | What it does |
|---|---|---|
| `web` | GitHub `shreyysk/MixMint`, branch `launch-prep` (Dockerfile) | The site. Test address: `web-production-238db.up.railway.app` |
| `cron` | image `alpine:3.20`, schedule `5 1-5 * * *` | Calls `/cron/<job>/` on web with `CRON_SECRET` (same jobs and hours as `vercel.json`) |

Already set on `web`: DEBUG, ENVIRONMENT, ALLOWED_HOSTS, BASE_URL, APP_URL, NUM_PROXIES, DEFAULT_PAYMENT_GATEWAY,
EMAIL_PROVIDER, WEB_CONCURRENCY, DB_TRANSACTION_POOLER, PORT=8080. `cron` reads `CRON_SECRET` and the address from `web`.
Still to add on `web`: the secret keys listed in Step 2 below.

### DNS at Hostinger (hPanel → Domains → mixmint.site → DNS / Nameservers)
Remove the old Vercel records first (the `@` A record and the `www` CNAME), then add:

| Type | Name | Value |
|---|---|---|
| ALIAS | `@` | `cnbh8fzt.up.railway.app` |
| TXT | `_railway-verify` | `railway-verify=ea0ba25dcf7c2b7bddebeaee32264777355eba361d366e9518a77f6f8049f708` |
| CNAME | `www` | `t1119xb2.up.railway.app` |
| TXT | `_railway-verify.www` | `railway-verify=4e909945d158a38d2d2bde5e617fdf04c852c086439c607d6d13f3a402caf35d` |

Keep the email records (MX, SPF, DKIM, Resend `send` / `resend._domainkey`) as they are.
Railway issues the HTTPS certificate on its own once the records are visible (minutes to an hour).

R2 storage and the Telegram setup (bot, vault channels, public channel, webhooks) stay exactly as they are.
Only the server that runs Django moves. Same domain, same URLs, same webhooks.

## What's in the repo for Railway
- `Dockerfile`: Python 3.12 + ffmpeg, static files built in, gunicorn with a 320 s timeout (vault and promo
  jobs keep their 300 s like on Vercel).
- `railway.json`: Dockerfile build, runs `migrate` before each deploy, health check on `/health/`.
- `python manage.py cron_tick`: runs the jobs that `vercel.json` used to schedule (same times, UTC).
- On Railway the app behaves like it did on Vercel: background tasks run inline (no extra worker to pay for)
  and big downloads are handed to short-lived R2 links.

## Step 1: Railway account (you)
1. Sign up at railway.com with GitHub, choose the **Hobby** plan ($5/month, includes $5 of usage).
2. New Project → **Deploy from GitHub repo** → `shreyysk/MixMint`, branch `launch-prep` for testing.
3. Service settings → Region: **Southeast Asia (Singapore)**, the closest to India.

## Step 2: Variables (you, in Railway → service → Variables → Raw Editor)
Copy these from where they came from (Vercel marks them "sensitive", so it can't show them again):

| Variable | Where to get the value |
|---|---|
| `SECRET_KEY` | Your saved copy. **Use the same one as Vercel** or everyone gets logged out and old links stop working. If lost, generate a new long random one. |
| `DEBUG` | `False` |
| `ENVIRONMENT` | `production` |
| `ALLOWED_HOSTS` | `mixmint.site,www.mixmint.site,.up.railway.app` |
| `BASE_URL`, `APP_URL` | `https://mixmint.site` |
| `ADMIN_URL`, `ADMIN_EMAIL`, `FROM_EMAIL` | same as on Vercel |
| `NUM_PROXIES` | `1` |
| `DATABASE_URL` | Supabase → Project Settings → Database → Connection string (pooler, port 6543) |
| `CACHE_URL` | Upstash console → your Redis → `rediss://` URL (same as now) |
| `CRON_SECRET` | same as Vercel, or a new random string |
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT`, `R2_BUCKET_NAME`, `R2_PRIVATE_BUCKET`, `R2_PUBLIC_BUCKET`, `R2_PUBLIC_URL` | Cloudflare → R2 (you can create a new API token if you don't have the old secret) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_ADMIN_CHAT_ID`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | BotFather / my.telegram.org (same values) |
| `DEFAULT_PAYMENT_GATEWAY` | `cashfree` |
| `CASHFREE_PG_APP_ID`, `CASHFREE_PG_SECRET`, `CASHFREE_PG_ENV` | Cashfree → Developers → API keys; env `production` |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | Razorpay dashboard (backup gateway) |
| `RESEND_API_KEY` | Resend dashboard |
| `SMTP_USER`, `SMTP_PASSWORD` | Your Hostinger mailbox (e.g. `hello@mixmint.site`) and its password. Backup sender. **Only works on Railway Pro**: Hobby blocks outbound SMTP. |
| `SMTP_DAILY_LIMIT` | `100` on Hostinger's free/trial mail, `1000` on Business Starter |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google Cloud console (Google login) |
| `GOOGLE_DRIVE_API_KEY` | Google Cloud console (only if used) |

Not needed on Railway: `CELERY_TASK_ALWAYS_EAGER`, `CELERY_BROKER_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
`SUPABASE_SERVICE_ROLE_KEY` (the site doesn't use them).

Add later when ready: `TELEGRAM_CHANNEL_ID`, `TELEGRAM_ASSETS_CHANNEL_ID`, `PROMO_GITHUB_REPO`, `PROMO_GITHUB_TOKEN`,
Instagram/YouTube keys.

Email on Railway: Hobby blocks outbound SMTP (ports 465/587), so the Hostinger backup can't send from there.
Keep Resend as the main sender on Hobby, or move to Railway Pro to use the Hostinger mailbox.

## Step 3: Test on the Railway address
Settings → Networking → **Generate domain** (`something.up.railway.app`). Open it and check: home, a release,
login, DJ dashboard, admin. Nothing changes for real users yet.

## Step 4: Scheduled jobs
In the same project: **New → Empty service** from the same repo, name it `cron`.
- Settings → Deploy → Custom start command: `python manage.py cron_tick`
- Settings → Cron schedule: `5 * * * *` (every hour at :05; it runs a few seconds and stops)
- Same variables as the web service (Railway: "Shared variables" saves copying).

## Step 5: Switch the domain (5 minutes, no downtime)
1. Railway web service → Networking → Custom domain → add `mixmint.site` and `www.mixmint.site`.
2. At your DNS provider, point the records to what Railway shows (CNAME). Keep Vercel running until the new
   address works.
3. Telegram, Cashfree and Razorpay webhooks use `https://mixmint.site/...`, so nothing changes there. Optional:
   Admin → Support → Telegram bot → Reconnect.
4. After a week with no problems, pause the Vercel project (don't delete it yet).

## Step 6 (later): Database on Railway too
For one bill and faster pages (app and database in the same region): add Railway Postgres, copy the data
from Supabase with `pg_dump` / `pg_restore` (22 MB, a few minutes of maintenance mode), update `DATABASE_URL`.
Do this in a quiet hour; Admin → Settings → Maintenance mode first.

## Cost estimate
Hobby $5/month includes $5 of usage. One small web service (~0.5 GB RAM) plus the hourly cron is usually
about $5-10/month. Supabase, Upstash, R2, Resend stay on their free plans until you need more.
