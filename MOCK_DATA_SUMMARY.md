# 📊 BATCH 3: Mock Data Summary & Cleanup Instructions

## ✅ MOCK DATA CREATED

### Overview:
- **6 Test DJs** (all approved, ready to test)
- **8 Test Tracks** (5 paid, 3 free with prices: ₹0)
- **4 Test Album Packs** (3 paid, 1 free)

All test data is clearly marked with:
- `[TEST]` or `[FREE TEST]` in titles
- `[TEST DATA]` in DJ bios
- " Test" suffix in profile names

---

## 📋 DETAILED INVENTORY

### Test DJs:
1. **DJ Shadow Test** - Electronic/Downtempo/Hip-Hop
   - Slug: `dj-shadow-test`
   - Email: `dj-shadow-test@test.mixmint.local`
   - Has: 2 tracks, 1 album

2. **Luna Beats Test** - House/Techno/Deep House
   - Slug: `luna-beats-test`
   - Email: `luna-beats-test@test.mixmint.local`
   - Has: 2 tracks, 1 album

3. **Rhythm Master Test** - Drum & Bass/Jungle/Breakbeat
   - Slug: `rhythm-master-test`
   - Email: `rhythm-master-test@test.mixmint.local`
   - Has: 1 track, 1 album

4. **Bass Frequency Test** - Dubstep/Bass/Trap
   - Slug: `bass-frequency-test`
   - Email: `bass-frequency-test@test.mixmint.local`
   - Has: 1 track, 1 album

5. **Vinyl Soul Test** - Soul/Funk/Disco
   - Slug: `vinyl-soul-test`
   - Email: `vinyl-soul-test@test.mixmint.local`
   - Has: 1 track

6. **Cosmic Trance Test** - Trance/Progressive/Psytrance
   - Slug: `cosmic-trance-test`
   - Email: `cosmic-trance-test@test.mixmint.local`
   - Has: 1 track

### Test Tracks:
1. **Midnight Groove [TEST]** - ₹49 (paid)
2. **Sunrise Anthem [FREE TEST]** - ₹0 (free)
3. **Urban Jungle [TEST]** - ₹79 (paid)
4. **Bass Drop [TEST]** - ₹99 (paid)
5. **Soulful Sunday [FREE TEST]** - ₹0 (free)
6. **Cosmic Journey [TEST]** - ₹149 (paid)
7. **Minimal Techno 001 [TEST]** - ₹59 (paid)
8. **Funk Revival [FREE TEST]** - ₹0 (free)

### Test Albums:
1. **Summer Sessions 2026 [TEST]** - ₹299 (150MB)
2. **Underground Collection [TEST]** - ₹499 (200MB)
3. **Best of House [TEST]** - ₹399 (180MB)
4. **Bass Music Pack [FREE TEST]** - ₹0 (100MB)

---

## 🔐 TEST CREDENTIALS

All DJ accounts use the same password: **`TestPass123!`**

Format: `{slug}@test.mixmint.local`

Example:
- Email: `dj-shadow-test@test.mixmint.local`
- Password: `TestPass123!`

---

## 🎯 TESTING USE CASES

### Use This Mock Data To Test:

1. **DJ Discovery:**
   - Browse 6 different DJs
   - View various genres
   - Check profile pages

2. **Pricing Visibility:**
   - Verify NO prices on listing pages
   - Verify prices ONLY on detail pages
   - Check subscription pricing on DJ profiles

3. **Payment Flow:**
   - Test paid track purchase (₹49-₹149)
   - Test paid album purchase (₹299-₹499)
   - Test subscription purchase

4. **Free Content:**
   - 3 free tracks available
   - 1 free album pack
   - Verify bypasses payment flow
   - Still uses token system

5. **Mixed Content:**
   - DJs have both paid and free content
   - Verify correct button labels
   - Test both flows from same DJ

---

## 🧹 CLEANUP INSTRUCTIONS

### When To Clean Up:
- After completing all testing
- Before pushing to production
- When mock data is no longer needed

### How To Clean Up:

```bash
cd /app
node cleanup_mock_data.js
```

### What Gets Deleted:
✅ All tracks with `[TEST]` in title
✅ All albums with `[TEST]` in title  
✅ All DJ profiles with `[TEST DATA]` in bio
✅ All user profiles ending with " Test"
✅ Associated auth accounts

### What Stays Safe:
✅ Real user accounts
✅ Real content without [TEST] markers
✅ System settings
✅ Payment records
✅ Subscription records
✅ Email logs

### Cleanup Process:
1. Script shows 5-second countdown (cancel with Ctrl+C)
2. Deletes tracks (cascades to purchases if any)
3. Deletes albums (cascades to purchases if any)
4. Deletes DJ profiles
5. Deletes user profiles
6. Deletes auth accounts
7. Shows summary of deleted items

---

## ⚠️ IMPORTANT NOTES

### File Storage:
- Test files use placeholder `file_key` values
- Files don't actually exist in R2 bucket
- Download attempts will fail at file retrieval
- This is EXPECTED for testing
- Token generation and payment flow will work

### Email Testing:
- If Resend configured: real emails sent
- If not configured: logged with `[EMAIL_ERROR]`
- Purchase/subscription succeeds regardless

### Database Integrity:
- All foreign keys properly set
- Cascading deletes configured
- Safe to create purchases/subscriptions with test data
- Cleanup will remove test purchases too

### Re-running Seed:
- Script checks for existing records
- Won't create duplicates
- Safe to run multiple times
- Skips already existing test data

---

## 🔄 RE-SEEDING DATA

If you need to regenerate mock data:

```bash
# Clean up first
cd /app
node cleanup_mock_data.js

# Wait for completion, then re-seed
node seed_mock_data.js
```

---

## 📊 VERIFICATION QUERIES

### Check Mock Data Exists:
```sql
-- Count test DJs
SELECT COUNT(*) FROM dj_profiles 
WHERE bio LIKE '%[TEST DATA]%';

-- Count test tracks
SELECT COUNT(*) FROM tracks 
WHERE title LIKE '%[TEST]%';

-- Count test albums
SELECT COUNT(*) FROM album_packs 
WHERE title LIKE '%[TEST]%';

-- List all test DJs with content
SELECT 
    dp.dj_name,
    dp.slug,
    COUNT(DISTINCT t.id) as track_count,
    COUNT(DISTINCT ap.id) as album_count
FROM dj_profiles dp
LEFT JOIN tracks t ON t.dj_id = dp.id
LEFT JOIN album_packs ap ON ap.dj_profile_id = dp.id
WHERE dp.bio LIKE '%[TEST DATA]%'
GROUP BY dp.id, dp.dj_name, dp.slug;
```

### Check Free vs Paid Distribution:
```sql
-- Tracks by price
SELECT 
    CASE WHEN price = 0 THEN 'Free' ELSE 'Paid' END as type,
    COUNT(*) as count
FROM tracks
WHERE title LIKE '%[TEST]%'
GROUP BY CASE WHEN price = 0 THEN 'Free' ELSE 'Paid' END;

-- Albums by price
SELECT 
    CASE WHEN price = 0 THEN 'Free' ELSE 'Paid' END as type,
    COUNT(*) as count
FROM album_packs
WHERE title LIKE '%[TEST]%'
GROUP BY CASE WHEN price = 0 THEN 'Free' ELSE 'Paid' END;
```

---

## ✅ MOCK DATA CHECKLIST

Before starting manual tests:
- [ ] Mock data seeded successfully
- [ ] 6 DJs visible on `/explore`
- [ ] 8 tracks visible on `/tracks`
- [ ] 4 albums visible on `/albums`
- [ ] Test credentials work (can login)
- [ ] DJ profiles accessible via slug
- [ ] Mix of paid and free content present

After completing tests:
- [ ] All test scenarios executed
- [ ] Issues documented (if any)
- [ ] Mock data cleaned up
- [ ] Database verified clean
- [ ] Ready for next development phase

---

## 🚀 QUICK START

```bash
# 1. Ensure dev server is running
cd /app
yarn dev

# 2. Open browser
# http://localhost:3000

# 3. Follow testing guide
# See: /app/MANUAL_TESTING_GUIDE.md

# 4. When done, cleanup
node cleanup_mock_data.js
```

---

## 📞 TROUBLESHOOTING

### Issue: DJs not showing on explore page
**Check:** Navigate to `/explore` directly
**Query:** `SELECT * FROM dj_profiles WHERE status = 'approved' AND bio LIKE '%[TEST DATA]%';`

### Issue: Tracks not visible
**Check:** Navigate to `/tracks` directly
**Query:** `SELECT * FROM tracks WHERE title LIKE '%[TEST]%' AND status = 'active';`

### Issue: Login fails for test DJs
**Check:** Ensure password is exactly `TestPass123!`
**Verify:** Auth users exist in Supabase Auth dashboard

### Issue: Cleanup doesn't remove all data
**Manual cleanup SQL:**
```sql
-- Delete test tracks
DELETE FROM tracks WHERE title LIKE '%[TEST]%';

-- Delete test albums
DELETE FROM album_packs WHERE title LIKE '%[TEST]%';

-- Delete test DJ profiles
DELETE FROM dj_profiles WHERE bio LIKE '%[TEST DATA]%';

-- Delete test user profiles
DELETE FROM profiles WHERE full_name LIKE '%Test';
```

---

Generated: 2026-02-03  
For: MixMint Testing Phase  
Batch: 3 (Backend Hardening & Monetization)
