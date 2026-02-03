# 🧪 MixMint Manual Testing Guide

## 📊 MOCK DATA OVERVIEW

### Test Data Created:
- **6 DJs** (all approved, various genres)
- **8 Tracks** (5 paid, 3 free)
- **4 Album Packs** (3 paid, 1 free)

### Test Accounts:
All DJ accounts use password: `TestPass123!`

| DJ Name | Email | Genre Focus |
|---------|-------|-------------|
| DJ Shadow Test | dj-shadow-test@test.mixmint.local | Electronic/Downtempo |
| Luna Beats Test | luna-beats-test@test.mixmint.local | House/Techno |
| Rhythm Master Test | rhythm-master-test@test.mixmint.local | Drum & Bass |
| Bass Frequency Test | bass-frequency-test@test.mixmint.local | Dubstep/Bass |
| Vinyl Soul Test | vinyl-soul-test@test.mixmint.local | Soul/Funk |
| Cosmic Trance Test | cosmic-trance-test@test.mixmint.local | Trance |

---

## 🚀 TESTING WORKFLOW

### Prerequisites:
1. Development server running: `yarn dev`
2. Browser open: http://localhost:3000
3. Razorpay TEST mode active

---

## TEST SCENARIO 1: Explore & Browse DJs

**Objective:** Verify DJ discovery and profile pages

### Steps:
1. Navigate to http://localhost:3000/explore
2. **Expected:** See 6 test DJs in grid layout
3. **Verify:** 
   - ❌ NO prices shown on cards
   - ✅ DJ names visible
   - ✅ Genre tags displayed
   - ✅ Cards are clickable

4. Click on "DJ Shadow Test"
5. **Expected:** Navigate to `/dj/dj-shadow-test`
6. **Verify:**
   - ✅ Banner image displayed
   - ✅ DJ bio shown
   - ✅ Genre tags visible
   - ✅ Tracks section (should show 2 tracks)
   - ✅ Albums section (should show 1 album)
   - ❌ NO prices on track/album cards
   - ✅ Subscription CTA at bottom

---

## TEST SCENARIO 2: Browse All Tracks

**Objective:** Verify track listing page

### Steps:
1. Navigate to http://localhost:3000/tracks
2. **Expected:** See 8 test tracks in grid
3. **Verify:**
   - ❌ NO prices shown on cards
   - ✅ Track titles visible
   - ✅ DJ names clickable
   - ✅ Preview button (if YouTube URL exists)
   - ✅ "Buy Now" or similar button

4. Search for "FREE" in browser (Ctrl+F)
5. **Expected:** 3 free tracks visible but prices NOT shown on cards

---

## TEST SCENARIO 3: Purchase Paid Track

**Objective:** Test complete payment flow

### Steps:
1. From `/tracks`, click any paid track (e.g., "Midnight Groove [TEST]")
2. **Expected:** Navigate to track detail page
3. **Verify:**
   - ✅ Price NOW visible: "₹49"
   - ✅ Button shows: "Download - ₹49" or "Buy Now"
   - ✅ DJ name clickable
   - ✅ Preview available (if YouTube URL)

4. Click purchase button
5. **Expected:** Razorpay modal opens
6. **Verify:**
   - ✅ Amount shown: ₹49.00
   - ✅ MixMint branding
   - ✅ Order description visible

7. **Use Razorpay Test Card:**
   - Card Number: `4111 1111 1111 1111`
   - CVV: Any 3 digits
   - Expiry: Any future date
   - Name: Any name

8. Complete payment
9. **Expected:** 
   - ✅ Redirect to `/payment/success`
   - ✅ Success message displayed
   - ✅ "Go to Library" button visible

10. Check email (if Resend configured)
11. **Expected:** Purchase confirmation email received

12. Check browser console
13. **Verify logs:**
    ```
    [PAYMENT_ORDER_CREATED] ...
    [PAYMENT_VERIFIED] ...
    [PURCHASE_COMPLETE] ...
    [EMAIL_SENT] ... or [EMAIL_ERROR] ...
    ```

---

## TEST SCENARIO 4: Free Track Download

**Objective:** Verify free content bypasses payment

### Steps:
1. Navigate to `/tracks`
2. Click "Sunrise Anthem [FREE TEST]"
3. **Expected:** Navigate to track detail page
4. **Verify:**
   - ❌ NO price shown
   - ✅ Button shows: "Free Download"
   - ✅ NO payment modal

5. Click "Free Download"
6. **Expected:** 
   - ✅ Download token requested
   - ✅ Download initiated OR
   - ⚠️  Error (expected, as files don't exist in R2)

**Note:** Download will fail because test files don't exist in R2, but the flow should bypass payment correctly.

---

## TEST SCENARIO 5: Album ZIP Purchase

**Objective:** Test album pack purchase flow

### Steps:
1. Navigate to `/albums`
2. **Expected:** See 4 album packs
3. **Verify:**
   - ❌ NO prices on cards
   - ✅ Album titles visible
   - ✅ File sizes shown
   - ✅ DJ names clickable

4. Click "Summer Sessions 2026 [TEST]"
5. **Expected:** Navigate to album detail page
6. **Verify:**
   - ✅ Price NOW visible: "₹299"
   - ✅ Button shows: "Buy Pack" or "Download - ₹299"
   - ✅ Description visible
   - ✅ File size displayed

7. Complete purchase using Razorpay test card
8. **Expected:** Same flow as track purchase

---

## TEST SCENARIO 6: Subscription Flow

**Objective:** Test DJ subscription payment

### Steps:
1. Navigate to DJ profile: `/dj/luna-beats-test`
2. Scroll to subscription section
3. **Verify:**
   - ✅ Prices shown (Basic/Pro/Super)
   - ✅ Quota information visible
   - ✅ Subscribe buttons present

4. Click "Subscribe - Basic" (₹49)
5. **Expected:** Razorpay modal opens
6. **Verify:**
   - ✅ Amount: ₹49.00
   - ✅ Description includes "Basic Subscription"

7. Complete payment
8. **Expected:**
   - ✅ Subscription created in database
   - ✅ Email sent with quota details
   - ✅ Success page

9. Check database:
   ```sql
   SELECT * FROM dj_subscriptions 
   WHERE user_id = 'your_user_id' 
   ORDER BY created_at DESC 
   LIMIT 1;
   ```

---

## TEST SCENARIO 7: Admin Dashboard

**Objective:** Verify admin settings functionality

### Prerequisites:
- Admin user account (role='admin')
- If needed, update existing user:
  ```sql
  UPDATE profiles 
  SET role = 'admin' 
  WHERE email = 'your@email.com';
  ```

### Steps:
1. Login as admin user
2. Navigate to `/admin/settings`
3. **Expected:** Settings page loads
4. **Verify:**
   - ✅ Payment Gateway section visible
   - ✅ Razorpay selected, Test mode active
   - ✅ Minimum Pricing section
   - ✅ Feature Flags section

5. Toggle payment mode: Test → Production
6. Click "Save Payment Gateway"
7. **Expected:** 
   - ✅ Success message
   - ✅ Database updated

8. Check database:
   ```sql
   SELECT value FROM system_settings 
   WHERE key = 'payment_gateway';
   ```

9. Change minimum track price: ₹29 → ₹39
10. Click "Save Pricing"
11. **Expected:** Success confirmation

12. Toggle feature flag: "Fan Uploads Enabled" → OFF
13. Click "Save Feature Flags"
14. **Expected:** Success confirmation

---

## TEST SCENARIO 8: Pricing Visibility Rules

**Objective:** Confirm prices shown ONLY at intent moment

### Verification Checklist:

| Page | Prices Should Be | Actual |
|------|------------------|--------|
| `/explore` | ❌ NOT visible | |
| `/tracks` (listing) | ❌ NOT visible | |
| `/albums` (listing) | ❌ NOT visible | |
| `/track/[id]` (detail) | ✅ VISIBLE | |
| `/album/[id]` (detail) | ✅ VISIBLE | |
| `/dj/[slug]` (subscription) | ✅ VISIBLE | |
| `/dashboard` | ❌ NOT visible | |

**Test Method:**
1. Open each page
2. Use browser Find (Ctrl+F) to search for "₹"
3. Record results in table above

---

## TEST SCENARIO 9: Error Handling

**Objective:** Verify proper error messages

### Test Cases:

#### 9.1: Payment Failure
1. Attempt purchase
2. In Razorpay modal, click "Cancel" or close
3. **Expected:** Remain on page or show retry option

#### 9.2: Invalid Content
1. Navigate to non-existent track: `/track/invalid-uuid`
2. **Expected:** 
   - ✅ Error page or 404
   - ✅ Clear message
   - ✅ Navigation option

#### 9.3: Unauthorized Access
1. Logout
2. Navigate to `/admin/settings`
3. **Expected:**
   - ✅ Redirect to login OR
   - ✅ "Unauthorized" message

---

## TEST SCENARIO 10: Free vs Paid Content Mix

**Objective:** Verify correct behavior for both content types

### Steps:
1. Navigate to `/dj/luna-beats-test`
2. **Expected:** See both paid and free tracks
3. **Verify:**
   - ❌ NO prices on cards
   - ✅ Both types displayed equally

4. Click free track: "Sunrise Anthem [FREE TEST]"
5. **Verify:** "Free Download" button (no price)

6. Go back, click paid track: "Minimal Techno 001 [TEST]"
7. **Verify:** "Download - ₹59" button

---

## 📊 TESTING CHECKLIST

### Frontend UI/UX
- [ ] Explore page loads and displays DJs
- [ ] DJ profile pages show tracks and albums
- [ ] Track listing page functional
- [ ] Album listing page functional
- [ ] Search functionality (if implemented)
- [ ] Mobile responsive design
- [ ] Loading states display correctly
- [ ] Error states handled gracefully

### Pricing Visibility
- [ ] ❌ NO prices on explore page
- [ ] ❌ NO prices on track cards
- [ ] ❌ NO prices on album cards
- [ ] ✅ Prices on track detail page
- [ ] ✅ Prices on album detail page
- [ ] ✅ Subscription prices on DJ profile

### Payment Flow
- [ ] Razorpay modal opens correctly
- [ ] Test card payments succeed
- [ ] Payment verification works
- [ ] Purchase records created
- [ ] Emails sent (or logged if failed)
- [ ] Success page displays
- [ ] Failed payments handled

### Free Content
- [ ] Free tracks identified correctly
- [ ] No payment flow for free content
- [ ] Download attempts for free content
- [ ] "Free Download" button displays

### Admin Dashboard
- [ ] Admin-only access enforced
- [ ] Payment gateway toggle works
- [ ] Pricing updates save correctly
- [ ] Feature flags toggle
- [ ] Success/error messages display

### Security
- [ ] Non-admin cannot access `/admin/*`
- [ ] Signature verification prevents tampering
- [ ] Old deprecated APIs return 410
- [ ] RLS policies enforced

---

## 🐛 KNOWN ISSUES / EXPECTED BEHAVIORS

### ⚠️  Expected "Errors":
1. **Download Failures:** 
   - Test files don't exist in R2 bucket
   - Token generation works, actual download fails
   - This is EXPECTED behavior for testing

2. **Email Failures (if Resend not configured):**
   - Emails won't send
   - Check console for `[EMAIL_ERROR]`
   - Purchase/subscription still succeeds

3. **PhonePe Not Available:**
   - Selecting PhonePe will fail
   - Expected: "PhonePe not configured" error
   - Switch back to Razorpay

---

## 📝 LOGGING & DEBUGGING

### Check Backend Logs:
```bash
# View all logs
tail -f /tmp/next_dev.log

# Filter payment logs
grep "PAYMENT" /tmp/next_dev.log

# Filter email logs
grep "EMAIL" /tmp/next_dev.log
```

### Check Browser Console:
Open DevTools (F12) and monitor:
- Network tab for API calls
- Console for JavaScript errors
- Application tab for auth state

### Database Queries:
```sql
-- Recent purchases
SELECT * FROM purchases 
ORDER BY created_at DESC 
LIMIT 10;

-- Active subscriptions
SELECT * FROM dj_subscriptions 
WHERE expires_at > NOW() 
ORDER BY created_at DESC;

-- System settings
SELECT * FROM system_settings;
```

---

## 🧹 CLEANUP AFTER TESTING

When testing is complete:

```bash
cd /app
node cleanup_mock_data.js
```

**This will delete:**
- All test DJs
- All test tracks (with [TEST] in title)
- All test albums (with [TEST] in title)
- All test user accounts

**This will NOT delete:**
- Real users
- Real content
- System settings
- Payment records
- Email logs

---

## ✅ TEST COMPLETION CRITERIA

Mark each as complete:
- [ ] All 10 test scenarios executed
- [ ] Pricing visibility rules verified
- [ ] Payment flow works end-to-end
- [ ] Free content bypasses payment correctly
- [ ] Admin dashboard functional
- [ ] No critical bugs found
- [ ] UI/UX meets production standards
- [ ] Mock data cleaned up

---

## 📤 REPORTING ISSUES

If you find bugs, document:
1. **Scenario:** Which test scenario
2. **Steps:** Exact steps to reproduce
3. **Expected:** What should happen
4. **Actual:** What actually happened
5. **Logs:** Relevant console/backend logs
6. **Screenshots:** If applicable

---

## 🎯 NEXT STEPS AFTER TESTING

Once testing is complete:
1. Review all findings
2. Prioritize bug fixes
3. Decide on next batch:
   - Track/Album detail pages
   - User dashboard improvements
   - DJ dashboard improvements
   - Production readiness
