# MixMint Go-Live Checklist

## 1. Security & Auth
- [x] Admin emails verified and role assigned correctly in Supabase.
- [x] RLS policies active on all tables (`purchases`, `tracks`, `referrals`, etc.).
- [x] Authentication flows tested on multiple browsers.
- [x] Rate limits verified on high-risk APIs.

## 2. Payments (Razorpay)
- [x] Razorpay account in "Live" mode.
- [x] Live Key ID and Secret configured in production environment.
- [x] Webhook for payment confirmation verified (if applicable).
- [x] Successful small-amount transaction performed on production.

## 3. Storage (Cloudflare R2)
- [x] CORS policies configured correctly for `upload` and `download`.
- [x] Bucket permissions restricted (Public read-only for thumbnails, private for source files).
- [x] Storage paths verified: `/<dj_slug>_<dj_id>/...`

## 4. Legal & Compliance
- [x] Terms of Service page live and accurate.
- [x] Privacy Policy page live and accurate.
- [x] Disclaimer (regarding piracy and intellectual property) present on upload.

## 5. Reliability
- [x] GitHub Actions (CI) passing on `main`.
- [x] Error logging (logger.alert) integrated into payment path.
- [x] Backup schedule active in Supabase.
- [x] Support email (`contact@mixmint.site`) functional.

## 6. Soft Launch Plan
- [x] Invite 3-5 "Founding DJs" for initial content.
- [x] Set "Enable Transcoding" to false initially to save resources.
- [x] Monitor logs for 24 hours after first live purchase.
