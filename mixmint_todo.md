

# 📝 `to-do.md`

**MixMint — Phased Execution Plan**

> This is written as a **real engineering task list**, not theory.
> Each phase can be assigned to a dev or an AI agent.

---

## PHASE 0 — FOUNDATION & SETUP

### Repo & Environment

* [ ] Initialize Next.js (App Router, TypeScript)
* [ ] Setup Tailwind CSS
* [ ] Setup ESLint + Prettier
* [ ] Setup environment variables structure
* [ ] Setup production & staging configs

### Supabase

* [ ] Create Supabase project
* [ ] Enable email auth
* [ ] Enable OAuth (Google)
* [ ] Create `profiles` table
* [ ] Sync `profiles.id = auth.users.id`
* [ ] Enable RLS globally

### Cloudflare R2

* [ ] Create private bucket
* [ ] Disable public access
* [ ] Setup access keys
* [ ] Test server-only access

---

## PHASE 1 — AUTH & CORE USER SYSTEM

### Authentication

* [ ] Signup / Login UI
* [ ] Session persistence
* [ ] Logout
* [ ] Email verification
* [ ] Password reset

### User Roles

* [ ] Role enum (user | dj | admin)
* [ ] Role-based route guards
* [ ] Protected routes

---

## PHASE 2 — DJ ONBOARDING & PROFILES

### DJ Application

* [ ] DJ application form
* [ ] Store application status
* [ ] Admin approval flow
* [ ] Approval / rejection emails

### Public DJ Profile

* [ ] DJ storefront page
* [ ] Profile image upload
* [ ] Bio & social links
* [ ] Public track / album listing

---

## PHASE 3 — CONTENT UPLOAD SYSTEM

### Track Upload

* [ ] Audio file validation
* [ ] Upload quota enforcement
* [ ] Metadata input (BPM, genre)
* [ ] YouTube preview requirement
* [ ] Save file path in DB

### Album / ZIP Upload

* [ ] Multi-track selection
* [ ] ZIP generation service
* [ ] Direct ZIP upload support
* [ ] Tracklist validation
* [ ] ZIP attempt limits

### Fan Uploads

* [ ] Super-only eligibility check
* [ ] Monthly limit enforcement
* [ ] Reset cron job

---

## PHASE 4 — PAYMENTS & PURCHASES

### Payments

* [ ] Razorpay integration
* [ ] Stripe integration
* [ ] Secure checkout flow
* [ ] Webhook handling
* [ ] Idempotency protection

### Purchase Records

* [ ] Track purchase table
* [ ] Album purchase table
* [ ] Ownership validation helpers

---

## PHASE 5 — SUBSCRIPTIONS & QUOTAS

### Subscription System

* [ ] Plan definitions (Basic/Pro/Super)
* [ ] Per-DJ subscriptions
* [ ] Start / cancel / renew
* [ ] Expiry handling

### Quota Tracking

* [ ] Monthly usage counters
* [ ] Quota reset cron
* [ ] Purchase override logic

---

## PHASE 6 — DOWNLOAD & SECURITY (CRITICAL)

### Download Tokens

* [ ] Token DB table
* [ ] Token generator
* [ ] Expiry enforcement
* [ ] IP locking
* [ ] One-time use check

### Secure Download API

* [ ] `/api/download/init`
* [ ] `/api/download/file`
* [ ] R2 streaming proxy
* [ ] Attempt decrement logic

---

## PHASE 7 — DJ ANALYTICS & EARNINGS

### Analytics

* [ ] Sales aggregation
* [ ] Download stats
* [ ] Subscriber count
* [ ] Top content ranking

### Earnings

* [ ] DJ earnings calculation
* [ ] Platform commission logic
* [ ] Withdrawal requests
* [ ] Payout status tracking

---

## PHASE 8 — POINTS & REFERRALS

### Points

* [ ] Points earning rules
* [ ] Checkout discount logic
* [ ] Max cap enforcement

### Referrals

* [ ] Referral links
* [ ] Qualification checks
* [ ] Admin approval flow

---

## PHASE 9 — ADMIN PANEL

### Core Admin

* [ ] Admin auth guard
* [ ] DJ approval queue
* [ ] User management
* [ ] Content moderation

### Advanced Admin

* [ ] DMCA management
* [ ] Abuse reports
* [ ] Payout approvals
* [ ] Audit logs

---

## PHASE 10 — POLISH & SCALE

### UX Polish

* [ ] Empty states
* [ ] Error messages
* [ ] Loading skeletons

### Performance

* [ ] Caching strategy
* [ ] Rate limiting
* [ ] CDN optimization

### Legal & Compliance

* [ ] Terms & Privacy
* [ ] GDPR data export/delete
* [ ] Copyright metadata

