# MixMint 2.0 — Audit fixes (September 2026)

All changes are covered by the test suite: **341 tests pass** (`pytest tests apps`), including
`tests/test_security_fixes.py` (41 new regression tests that each reproduce one of the bugs below).

## Before you deploy — required actions

1. **Run migrations** (`python manage.py migrate`). New migrations: `accounts 0008`, `commerce 0009`,
   `downloads 0004`, plus the SimpleJWT token blacklist tables. Render / Railway / Procfile now migrate on start.
2. **Install new requirements**: `pyotp` (2FA was crashing without it) plus security upgrades: Django 5.2.17, DRF 3.17.2, PyJWT 2.13.0, social-auth 6.0.1/5.0.0, requests 2.34.2, Razorpay SDK 2.0.1 (no more `setuptools<81` pin). `pip-audit` reports no known vulnerabilities.
3. **New / changed environment variables** (see `.env.example`):
   | Variable | Why |
   |---|---|
   | `RAZORPAY_WEBHOOK_SECRET` | Razorpay signs webhooks with the dashboard *webhook* secret, not the API key secret. Without it, Razorpay webhooks are rejected. |
   | `NUM_PROXIES` | How many proxies sit in front of Django (1 on Render/Railway/Vercel, 2 behind Cloudflare). Used to read the real client IP safely. |
   | `CACHE_URL` (recommended) | e.g. `redis://…`. Rate limits and fraud counters are only shared across workers with a real cache. |
   | `R2_PRIVATE_BUCKET` | `R2_BUCKET_NAME` still works as an alias. |
   | `BASE_URL` | Must be your public https URL — used for payment return URLs. |
4. **Razorpay dashboard → Webhooks**: URL `<BASE_URL>/api/v1/payments/webhook/razorpay/`,
   events `payment.captured`, `payment.failed`, `order.paid`.
5. **Cron (free tier)**: add two jobs — `/cron/release-escrow/` hourly and `/cron/payouts/` weekly
   (send `X-Cron-Secret`). Celery beat also has an hourly escrow task.
6. Production now **refuses to start with `DEBUG=True`** or an empty/`django-insecure` `SECRET_KEY`.

## Critical (money / access)

| # | Bug | Fix |
|---|---|---|
| 1 | Any pending (unpaid) purchase granted a download token | Only `status="paid"`, non-revoked purchases grant access (`DownloadManager.owned_purchase`) |
| 2 | Any logged-in user could DELETE any track | Owner-only (or staff); delete is now a soft delete |
| 3 | Any logged-in user could edit/delete any album | Approved-DJ create, owner-only edit/delete, soft delete |
| 4 | `is_redownload: true` gave anyone 50% off | Re-download price only for owners whose 3-day lock has passed |
| 5 | Cart checkout charged 100× (paise × 100) | All cart maths in paise; per-item amounts sum exactly to the charge |
| 6 | PhonePe return + webhook URLs pointed at routes that don't exist | Fixed to `/api/v1/payments/…`; old `/payment/…` URLs kept as aliases for in-flight orders |
| 7 | Downloads failed and **froze buyers' accounts** behind a proxy | One trusted-proxy-aware `get_client_ip`; a network change alone no longer freezes |
| 8 | DJs could create tracks under another DJ | `dj` is read-only and set from the logged-in DJ |
| 9 | Razorpay flow could never complete | Real checkout.js flow: order id stored, signed confirm endpoint (`/api/v1/payments/razorpay/confirm/`), webhook secret, `authorized` ≠ failed, capture on confirm |
| — | `ProfileViewSet` let users PATCH `role="admin"`, `is_pro_dj`, quotas… | Only `full_name`/`avatar_url` writable |
| — | Public DJ API exposed bank account, IFSC, UPI, PAN, **2FA secret** and was writable by anonymous users | Read-only, public-safe fields only |
| — | Legacy `/commerce/verify-purchase/` could mint *paid* purchases with no payment check (PhonePe path) | Now only accepts a signed Razorpay result for an existing order |
| — | Album page linked the raw external source URL (free download of paid albums) | External albums go through the signed, ownership-checked token flow |

## Payments & money

- **One fulfilment path** (`apps/payments/services.complete_order`) for callback, both webhooks and Razorpay confirm:
  row-locked, amount-verified, idempotent. Fixes double crediting and missing invoices.
- DJ split excludes the buyer platform fee; collaborator shares + owner remainder; commission stored on the purchase.
- **Escrow works**: sales credit escrow, `release_escrow` moves them to available after 24h/48h, payouts pay only available
  money, refunds reverse every credit. Weekly payouts no longer crash (`dj__user__payout_frozen` field error).
- Refunds reverse DJ earnings, use the purchase's own gateway, and never auto-refund delivered files.
- Download Insurance: correct amount (₹49 not 49 paise), goes through the normal order flow, activates only when paid.
- DJ application fee and Pro upgrade are now real orders that activate on payment (they never did before).
- Admin gateway toggle is honoured; quick-checkout / mobile quick-buy reuse the validated checkout.
- Referral bonuses are finally paid (after the referred DJ's first sale clears escrow); bonuses are withdrawable.

## Security hardening

- Client IP: never trusts the left-most `X-Forwarded-For` (blacklist / IP-lock bypass).
- Download tokens: atomic single use; shared link (other network **and** other device) freezes; owner check.
- CSRF cookie readable by JS again (all AJAX POSTs were 403 in production); `CSRF_TRUSTED_ORIGINS`.
- CSP now applies in every environment (it was silently blocking all inline JS in development) and allows exactly
  the hosts the site uses (Razorpay, YouTube/Instagram embeds, fonts); `/csp-report/` exists.
- Preview embeds: only YouTube/Instagram iframes built from a parsed video id (no arbitrary framing / attribute injection).
- SSRF guard now validates **every redirect hop before connecting**; Drive API key moved out of URLs.
- Brute-force limits: login (per IP + per account), sign-up, password reset, waitlist, support tickets, TOTP codes.
- Payout 2FA: TOTP secret only shown during setup, replay + brute-force protection; payouts row-locked.
- Session network binding uses /24 (/48 IPv6) so mobile users aren't logged out constantly.
- Bundles can only contain the DJ's own tracks; custom domains validated and unique.
- CSV export formula-injection safe; Telegram errors no longer log the bot token.
- ZIP-bomb limits on album processing; JSON chart data via `json_script`; pinned CDN scripts; duplicate Alpine removed.
- Secrets/DEBUG production guards; `ENVIRONMENT` defaults to production on Render/Railway/Vercel/Heroku.
- JWT refresh-token blacklist actually enabled.

## Crashes & broken features fixed

`/sitemap.xml` (and wrong URLs in it) · mobile home / track API · DJ onboarding status · custom-domain status for non-DJs ·
2FA setup (`pyotp`) · `update_weekly_sales` + `reset_quotas` cron jobs · re-download price TypeError ·
insurance buy/verify · request payout OTP · A/B experiments list · admin flagged-content & offer save ·
notifications with bad `limit` · smart search bad params · search routes shadowed by the track router ·
UUID routes that could never match · paused-store template missing · album page and DJ storefront rendered
**without the site layout** (missing `{% extends %}`) · cart drawer `/checkout/` 404 · `confirm_payment` URL name ·
embed "Buy" link · emails pointing at `mixmint.in` · ID3 tags corrupting WAV/FLAC uploads (tags now MP3-only, checksum stored) ·
multi-line f-strings that break on Python < 3.12 (`.python-version` / `runtime.txt` pin 3.12) ·
test settings not overriding static storage (93 tests failed on a fresh clone) · CI missing `pytest-django`.

## UI / UX

- **Checkout that works for both gateways** (`static/js/mm.js`): Razorpay modal or PhonePe redirect, animated
  confirming/success overlay, clear cancel/failure messages, button loading states.
- Track & album pages: real **Buy & Download** button (was cart-only), re-download price shown, lock message,
  logged-out buyers return to the page and checkout resumes automatically, sticky mobile buy bar.
- **Library rebuilt**: download / re-download / invoice PDF / refund actions per item, status badges, search,
  tabs with counts, skeleton loading, auto-refresh while a payment is confirming.
- Cart: exact paise display, "you pay" includes all charges, progress bar to the next bundle tier (tiers were mislabelled).
- Download page: real server-verified completion instead of a fake 8-second progress bar.
- Mobile bottom tab bar (Home · Search · Library · Profile), 48px touch targets, iOS zoom fix.
- Accessibility: focus-visible, `aria-live` toasts, labelled icon buttons, progressbar roles, better light-theme
  contrast (WCAG AA), reduced-motion support, no more global `* { transition }` jank.
- Auth: form values kept on error, network-change notice, busy states, password rules shown, confirm-password checked.

## Launch prep (round 2)

- Razorpay **test mode**: with `rzp_test_` keys a yellow "TEST MODE" banner shows site-wide and production boots with a warning.
  Going live later = swap to `rzp_live_` keys + live webhook secret in Vercel and redeploy. No code change.
- **Vercel Cron** jobs added in `vercel.json` (escrow release, renewals, clean-up, weekly sales daily; payouts Fridays).
  Cron URLs now accept Vercel's `Authorization: Bearer <CRON_SECRET>`.
- 2FA setup shows a real **QR code** (`segno`); DJs can **delete bundles**; payout, Pro-expiry and storage-overage **emails** are sent.
- Fixed: payout email crashed (`BankAccount` model does not exist).
- `pip-audit`: no known vulnerabilities. 346 tests pass.
- **Large downloads on Vercel**: files over 40 MB (`DOWNLOAD_PROXY_MAX_MB`) are handed to a 2-minute R2 signed URL after all
  token/ownership checks, so Vercel's function limits can't cut them off. Small files still stream through the verified proxy.
- **Migrations run automatically** on Vercel production builds (`pyproject.toml` build script); preview builds skip them.
- CI workflow installs `pytest pytest-django pytest-cov`. 348 tests pass.
