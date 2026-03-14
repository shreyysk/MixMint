# MixMint 2.0 - Project Requirements & Progress Document

## Project Overview
MixMint is a DJ-first digital music distribution platform operating in India with:
- **Backend**: Django 5.1 + Django REST Framework
- **Database**: Supabase PostgreSQL (Production) / SQLite (Dev)
- **Storage**: Cloudflare R2 (Private & Public buckets)
- **Payments**: PhonePe (Production) / Razorpay (Dev)
- **Email**: Resend

## User Personas
1. **Buyer/User**: Purchases and downloads tracks
2. **DJ**: Uploads, prices, and sells tracks (requires approval)
3. **Admin**: Platform management, moderation, revenue analytics

## Core Requirements
- Secure download system with IP binding, device hash, 3-attempt limit
- PhonePe payment integration with webhook signature verification
- DJ application workflow with ₹99 fee
- Pro DJ upgrade (8% commission vs 15% standard)
- Admin controls: freeze/ban accounts, kill switch, maintenance mode

---

## Implementation Progress

### Phase 1 - Bug Fixes (Completed: Jan 14, 2026)

#### CRITICAL Bug Fixed
- **BUG-001 (CP-03.06)**: PhonePe webhook signature verification - FIXED

#### HIGH Bugs Fixed
- **CP-02.01**: Track list API public access - FIXED
- **CP-02.04**: XSS sanitization for search - FIXED
- **CP-06.02**: Min track price ₹29 - FIXED
- **CP-06.04/05**: DJ role check for uploads - FIXED

### Phase 2 - Bug Fixes (Completed: Jan 14, 2026)

#### CRITICAL Bugs Fixed
- **P2-01.02**: Dashboard undefined variables (wallet, is_dj) - FIXED
- **P2-02.02**: DJ track isolation (`/api/tracks/my-tracks/` endpoint) - FIXED

#### HIGH Bugs Fixed
- **P2-11.08**: Cart merge on login (`merge_guest_cart` action) - FIXED

#### Enhancements Added
- **CI Pipeline**: Automated webhook signature tests (`/app/tests/test_webhook_signatures.py`)

---

## Prioritized Backlog

### P0 (Critical) - Remaining Phase 2
- [ ] Dashboard KPIs accuracy (P2-01.03, P2-01.04)
- [ ] Collab revenue split edge cases (P2-04.x)
- [ ] Bulk download token security (P2-13.04)

### P1 (High) - Phase 3
- [ ] Security exploit fixes (EX-01.x - R2 direct access, token reuse)
- [ ] Fraud detection system
- [ ] Account deletion workflow
- [ ] Maintenance mode UI

---

## Next Tasks
1. Continue Phase 2 remaining bugs if requested
2. Security audit for R2 bucket access
3. Implement fraud detection middleware
