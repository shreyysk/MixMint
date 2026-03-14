# MixMint 2.0 - Project Requirements & Progress Document

## Project Overview
MixMint is a DJ-first digital music distribution platform operating in India.

**Tech Stack**: Django 5.1 + DRF, Supabase PostgreSQL, Cloudflare R2, PhonePe

---

## Implementation Progress

### Phase 1 - Bug Fixes ✅
- PhonePe webhook signature (BUG-001)
- Track API public access, XSS sanitization
- Min price ₹29, DJ role checks

### Phase 2 - Bug Fixes ✅
- Dashboard fixes, DJ track isolation
- Cart merge on login, CI webhook tests

### Phase 3 - Security Fixes ✅
- IP spoofing detection, rate limiting
- Account velocity checks
- Security middleware added

### Phase 4 - Enhancements ✅ (Jan 14, 2026)

#### Real-Time Fraud Alert System
- `/app/apps/admin_panel/fraud_notifier.py`
- Auto-emails admins for high/critical alerts
- Daily digest for medium/low alerts

#### DJ Conversion & Retention System
**New Files:**
- `/app/apps/commerce/dj_conversion.py` - Models
- `/app/apps/commerce/dj_conversion_views.py` - API endpoints

**Features:**
1. **Welcome Bonus**: ₹50 after first track upload
2. **Referral Program**: DJ earns ₹100, referred DJ earns ₹50 on first sale
3. **Milestone Rewards**: ₹25-₹500 for sales/earnings milestones
4. **Promo Codes**: Commission discounts for new DJs
5. **Onboarding Progress**: 5-step tracker with tips

**New API Endpoints:**
- `GET /api/commerce/dj/referral/` - Get referral code & stats
- `POST /api/commerce/dj/referral/apply/` - Apply referral code
- `POST /api/commerce/dj/promo/apply/` - Apply promo code
- `GET /api/commerce/dj/milestones/` - View milestone progress
- `GET /api/commerce/dj/onboarding/` - Onboarding checklist
- `GET /api/commerce/dj/dashboard-stats/` - Enhanced DJ dashboard

---

## DJ Conversion Features Summary

| Feature | DJ Benefit | Platform Benefit |
|---------|-----------|------------------|
| Welcome Bonus | ₹50 free | Encourages first upload |
| Referral | ₹100 per referral | Organic growth |
| Milestones | Up to ₹500 rewards | Retention |
| Promo Codes | Lower commission | New DJ acquisition |
| Onboarding | Guided setup | Faster activation |

---

## Prioritized Backlog

### P1 (High)
- [ ] Email templates for notifications
- [ ] Admin fraud dashboard UI
- [ ] Referral analytics dashboard

### P2 (Medium)
- [ ] Push notifications for milestones
- [ ] Social sharing for referrals
- [ ] A/B testing for onboarding
