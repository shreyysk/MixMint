# BATCH 3 - End-to-End Testing Checklist

## ✅ TESTING CHECKLIST

### 1. Environment & Configuration
- [ ] `.env.local` has all required credentials
- [ ] Razorpay TEST keys configured
- [ ] Resend API key configured
- [ ] Database migrations applied successfully
- [ ] `system_settings` table populated
- [ ] Payment gateway set to Razorpay (test mode)

### 2. Schema Migrations
- [ ] `album_packs.dj_profile_id` column exists
- [ ] All album records have `dj_profile_id` populated
- [ ] Foreign key constraint added
- [ ] Index created for performance
- [ ] Old `dj_id` column still intact (backwards compatibility)

### 3. Payment Gateway Abstraction
- [ ] `getPaymentProvider()` returns Razorpay instance
- [ ] `getPaymentConfig()` reads from database
- [ ] PhonePe provider exists but throws disabled error
- [ ] Payment provider selection works dynamically

### 4. Email Integration
- [ ] `sendPurchaseEmail()` function exists
- [ ] `sendSubscriptionEmail()` function exists
- [ ] Email retry logic (3 attempts) works
- [ ] Email failures are non-blocking
- [ ] Email logs show in console

### 5. Payment API Routes
- [ ] `POST /api/payment/create` - Creates Razorpay order
  - Input: `{ content_type, content_id, plan? }`
  - Output: `{ orderId, amount, keyId }`
  - Validates content exists
  - Calculates correct amount
- [ ] `POST /api/payment/verify` - Verifies payment
  - Input: `{ orderId, paymentId, signature, content_type, content_id, plan? }`
  - Verifies Razorpay signature
  - Creates purchase or subscription record
  - Sends confirmation email
  - Returns success

### 6. Deprecated APIs
- [ ] `POST /api/purchase` returns 410 Gone
- [ ] `POST /api/subscribe` returns 410 Gone
- [ ] Error messages explain new flow

### 7. Frontend Payment Integration
- [ ] `loadRazorpayScript()` loads SDK
- [ ] `purchaseContent()` function works
- [ ] `subscribeToDJ()` function works
- [ ] Payment modal opens
- [ ] Verification happens after payment
- [ ] Redirect to success/failed pages

### 8. Admin Dashboard
- [ ] `/admin/settings` page accessible to admin only
- [ ] Payment gateway toggle works (Razorpay/PhonePe)
- [ ] Mode toggle works (test/production)
- [ ] Minimum pricing fields editable
- [ ] Feature flags toggleable
- [ ] Changes save to database
- [ ] Success/error messages display

### 9. Security & Access Control
- [ ] Admin pages require admin role
- [ ] Payment APIs require authentication
- [ ] Signature verification works
- [ ] Amount tampering prevented
- [ ] RLS policies enforce admin-only access to system_settings

### 10. Download & Pricing Rules
- [ ] Prices NOT shown on explore pages
- [ ] Prices NOT shown on track/album cards
- [ ] Prices shown ONLY on detail pages
- [ ] "Download - ₹XX" button on paid content
- [ ] "Free Download" button for free content (price=0)
- [ ] Free downloads bypass payment
- [ ] Free downloads still use token system

---

## 🧪 TEST SCENARIOS

### Scenario 1: Purchase Track (Paid)
1. Navigate to `/tracks`
2. Click track card → goes to `/track/[id]`
3. See "Download - ₹XX" button
4. Click button → Razorpay modal opens
5. Complete payment (test card)
6. Verify signature → purchase created
7. Email sent
8. Redirect to `/payment/success`
9. Track appears in library

### Scenario 2: Purchase Track (Free)
1. Navigate to `/tracks`
2. Click free track card → goes to `/track/[id]`
3. See "Free Download" button (no price)
4. Click button → directly request download token
5. No payment flow
6. Download starts

### Scenario 3: Subscribe to DJ
1. Navigate to `/dj/[slug]`
2. See subscription plans with prices
3. Click "Subscribe - Basic/Pro/Super"
4. Razorpay modal opens with subscription amount
5. Complete payment
6. Verify signature → subscription created
7. Email sent with quota info
8. Redirect to success

### Scenario 4: Admin Changes Payment Gateway
1. Login as admin
2. Navigate to `/admin/settings`
3. Change provider to PhonePe
4. Save
5. Verify `system_settings` updated
6. Next payment attempt uses PhonePe (will fail with "not configured")

### Scenario 5: Email Failure Handling
1. Set invalid Resend API key
2. Complete purchase
3. Purchase succeeds
4. Email fails (logged but non-blocking)
5. User still gets purchase

---

## 🔍 VERIFICATION QUERIES

### Check Album Migration
```sql
SELECT id, title, dj_id, dj_profile_id 
FROM album_packs 
LIMIT 10;
```

### Check System Settings
```sql
SELECT * FROM system_settings;
```

### Check Recent Purchases
```sql
SELECT 
  p.id,
  p.user_id,
  p.content_type,
  p.price,
  p.payment_id,
  p.created_at
FROM purchases p
ORDER BY created_at DESC
LIMIT 10;
```

### Check Active Subscriptions
```sql
SELECT 
  ds.id,
  ds.user_id,
  ds.dj_id,
  ds.plan,
  ds.expires_at,
  ds.payment_id
FROM dj_subscriptions ds
WHERE expires_at > NOW()
ORDER BY created_at DESC;
```

---

## 📝 MANUAL TESTING STEPS

1. **Environment Check:**
   ```bash
   cd /app
   node check_settings.js
   node check_migration_status.js
   ```

2. **Start Dev Server:**
   ```bash
   yarn dev
   ```

3. **Test Payment Flow:**
   - Open browser: http://localhost:3000
   - Create test user account
   - Navigate to track/album
   - Initiate purchase
   - Use Razorpay test card: 4111 1111 1111 1111
   - Complete payment
   - Verify success

4. **Test Admin Dashboard:**
   - Login as admin (role='admin')
   - Navigate to `/admin/settings`
   - Toggle payment gateway
   - Save and verify

5. **Check Logs:**
   ```bash
   # Check for payment logs
   grep "PAYMENT" /tmp/next_dev.log
   
   # Check for email logs
   grep "EMAIL" /tmp/next_dev.log
   ```

---

## ✅ SUCCESS CRITERIA

- [ ] All environment variables configured
- [ ] All migrations successful
- [ ] Payment flow works end-to-end
- [ ] Emails sent (or logged if failed)
- [ ] Admin dashboard functional
- [ ] Old APIs deprecated properly
- [ ] No console errors
- [ ] Security rules enforced
- [ ] Pricing visibility rules followed
- [ ] Free download support works
