# MixMint Go-Live Checklist

## 1. Security & Auth
- [ ] Admin emails verified and role assigned correctly in Supabase.
- [ ] RLS policies active on all tables (`purchases`, `tracks`, `referrals`, etc.).
- [ ] Authentication flows tested on multiple browsers.
- [ ] Rate limits verified on high-risk APIs.

## 2. Payments (Razorpay)
- [ ] Razorpay account in "Live" mode.
- [ ] Live Key ID and Secret configured in production environment.
- [ ] Webhook for payment confirmation verified (if applicable).
- [ ] Successful small-amount transaction performed on production.

## 3. Storage (Cloudflare R2)
- [ ] CORS policies configured correctly for `upload` and `download`.
- [ ] Bucket permissions restricted (Public read-only for thumbnails, private for source files).
- [ ] Storage paths verified: `/<dj_slug>_<dj_id>/...`

## 4. Legal & Compliance
- [ ] Terms of Service page live and accurate.
- [ ] Privacy Policy page live and accurate.
- [ ] Disclaimer (regarding piracy and intellectual property) present on upload.

## 5. Reliability
- [ ] GitHub Actions (CI) passing on `main`.
- [ ] Error logging (logger.alert) integrated into payment path.
- [ ] Backup schedule active in Supabase.
- [ ] Support email (`contact@mixmint.site`) functional.

## 6. Soft Launch Plan
- [ ] Invite 3-5 "Founding DJs" for initial content.
- [ ] Set "Enable Transcoding" to false initially to save resources.
- [ ] Monitor logs for 24 hours after first live purchase.
