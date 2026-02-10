# PRODUCT REQUIREMENTS DOCUMENT (PRD)

## 1. Product Overview

**Product Name:** MixMint
**Tagline:** *Home of DJ Releases*

### What MixMint Is

MixMint is a **DJ-first digital distribution & monetization SaaS platform** where DJs sell **downloadable music** (tracks, ZIP packs, exclusives) directly to fans with **strict anti-piracy controls**.

> MixMint does **not stream audio**.
> It sells **ownership and controlled access**, enforced by backend security.

---

## 2. Core Product Principles (Non-Negotiable)

These rules override **all features and designs**.

### 2.1 No Streaming — Ever

* No hosted audio streaming
* No internal previews
* Only **external embeds** (YouTube, Instagram)

### 2.2 Access Before Delivery

Before any download:

* User must be authenticated
* Ownership OR subscription quota must be validated
* A **one-time, expiring token** must be issued

### 2.3 Zero Public Files

* No public URLs
* No permanent links
* No direct Cloudflare R2 access
* All downloads are **server-proxied**

---

## 3. Target Users & Roles

### 3.1 Listener (Fan / Buyer)

**Can**

* Browse DJs
* Preview via YouTube embeds
* Buy tracks / albums
* Subscribe to DJs
* Download owned content
* Earn & redeem points

**Cannot**

* Upload content
* Bypass quotas or limits

---

### 3.2 DJ (Artist / Partner)

**Can**

* Create public storefront
* Upload tracks & albums
* Create ZIP packs
* Offer subscriptions
* Upload fan-exclusive content
* View sales & analytics
* Withdraw earnings

**Cannot**

* Access admin tools
* Download other DJs’ paid content for free

---

### 3.3 Admin

**Can**

* Approve DJs
* Moderate content
* Handle DMCA & abuse
* Manage payouts
* Configure platform rules

**Goal:** Keep admin workload minimal, automation first.

---

## 4. Core User Flows

### 4.1 Listener Flow

1. Discover DJ
2. Preview track (external embed)
3. Login / Signup
4. Buy OR subscribe
5. Click download
6. Backend validates access
7. Token generated
8. File delivered securely

---

### 4.2 DJ Flow

1. Apply as DJ
2. Admin approval
3. Create profile
4. Upload content
5. Set pricing / plans
6. Promote releases
7. Earn & withdraw revenue

---

## 5. Content Types

### 5.1 Single Track

* One audio file
* Free or paid
* Purchase or subscription access
* Limited download attempts

**Storage**

```
tracks/{dj_id}/{track_id}.wav
```

---

### 5.2 Album / ZIP Pack

* Multiple tracks bundled
* Always paid
* Higher price
* Strict attempt limits

**Upload Modes**

* Direct ZIP upload
* System-generated ZIP

**Storage**

```
zips/{dj_id}/{album_id}.zip
```

---

### 5.3 Fan Uploads (Super Tier Only)

* Exclusive single tracks
* Visible to all
* Downloadable only by Super subscribers
* Not purchasable

**Limits**

* 10 per month
* 3 attempts each
* Monthly reset

---

## 6. Subscription System (Per DJ)

No global subscriptions.

| Plan  | Tracks / Month | ZIPs | Fan Uploads |
| ----- | -------------- | ---- | ----------- |
| Basic | 5              | 0    | ❌           |
| Pro   | 20             | 1    | ❌           |
| Super | 40–50          | 2    | ✅ (10)      |

**Rules**

* 30-day validity
* Monthly reset
* No rollover
* Purchases override quotas

---

## 7. Download & Security System (Core IP)

### 7.1 Download Tokens

* Generated per click
* Expire in 2–5 minutes
* One-time use
* IP-locked on first use
* Stored in DB

### 7.2 Enforcement

* Token reuse blocked
* Expired tokens rejected
* Link sharing useless
* New click = new token

---

## 8. Payments & Monetization

### Revenue Streams

* Track sales
* Album / ZIP sales
* DJ subscriptions
* Platform commission
* Add-ons (custom domains, branding)

### Payments

* Razorpay / Stripe
* Secure checkout
* Refund management
* Tax handling (GST/VAT ready)

---

## 9. Points & Referrals

### Points

* Loyalty only
* Discount-based
* Cannot fully cover order
* Non-withdrawable

### Referrals

* User → User (points)
* DJ → DJ (cash after qualification)

---

## 10. Admin System (High Level)

Admins manage:

* DJ approvals
* Content moderation
* Abuse & DMCA
* Payouts
* Platform configuration

(Full admin spec will be detailed later.)

---

## 11. Success Metrics

* Conversion rate (visit → purchase)
* Subscription retention
* Download abuse rate (should be near zero)
* DJ revenue growth
* Platform commission growth

---

## 12. Out of Scope (Explicitly)

* Audio streaming
* Playlists with playback
* DRM plugins
* NFT / blockchain

---

