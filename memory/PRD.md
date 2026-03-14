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
- **BUG-001 (CP-03.06)**: PhonePe webhook signature verification was broken
  - **File**: `/app/apps/payments/phonepe.py`
  - **Fix**: Corrected `verify_payment()` method to properly generate and compare webhook signatures
  - **Status**: ✅ FIXED & TESTED

#### HIGH Bugs Fixed
- **CP-02.01**: Track list API was requiring auth
  - **File**: `/app/apps/tracks/views.py`
  - **Fix**: Added `get_permissions()` method returning `AllowAny` for list/retrieve
  - **Status**: ✅ FIXED & TESTED

- **CP-02.04**: XSS vulnerability in search queries
  - **Files**: `/app/apps/tracks/views.py`, `/app/apps/tracks/search_views.py`
  - **Fix**: Added `html.escape()` sanitization for search parameters
  - **Status**: ✅ FIXED

- **CP-06.02**: Minimum track price was ₹19, should be ₹29
  - **File**: `/app/config/settings.py`
  - **Fix**: Updated `MIN_TRACK_PRICE = 29.00`
  - **Status**: ✅ FIXED & TESTED

- **CP-06.04, CP-06.05**: DJ role check missing for track uploads
  - **File**: `/app/apps/tracks/views.py`
  - **Fix**: Added `_check_dj_permission()` method and enforced in `create()`/`update()`
  - **Status**: ✅ FIXED

#### Other Fixes
- Fixed lazy loading of payment gateway in settings to prevent import errors
- Updated pro upgrade views to use gateway-agnostic pattern
- Added `AllowAny` permissions to search endpoints

---

## Prioritized Backlog

### P0 (Critical) - Remaining Phase 1
- [ ] CP-04.x: Download token expiry/IP binding validation (Already implemented in utils.py)
- [ ] CP-07.x: Admin access control verification (Already uses IsAdminUser)

### P1 (High) - Phase 2
- [ ] Dashboard KPIs accuracy (P2-01.02, P2-01.03, P2-01.04)
- [ ] Collab revenue split calculation (P2-04.x)
- [ ] Cart merge on login (P2-11.08)
- [ ] Bulk download token security (P2-13.04)

### P2 (Medium) - Phase 3
- [ ] Security exploit fixes (EX-01.x)
- [ ] Fraud detection system
- [ ] Account deletion workflow

---

## Next Tasks
1. Run full test suite for Phase 1 fixes
2. Proceed to Phase 2 bug fixes when user confirms
3. Focus on DJ/Admin systems audit
