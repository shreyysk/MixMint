# 🎨 DESIGN DOCUMENT

**(UX, UI Structure, System Design — MixMint)**

This document explains **how MixMint should feel, behave, and be structured**, without tying us to implementation details yet.

---

## 1. Design Goals

### Primary UX Goals

* **Trust & ownership** → users feel they truly own files
* **Simplicity** → no clutter, no DJ-unfriendly UI
* **Security without friction** → strong protection, invisible to users
* **Speed** → downloads feel instant even with backend checks

### Secondary Goals

* Scales from indie DJs to labels
* Admin effort remains minimal
* Clear upgrade nudges (subscriptions, Super tier)

---

## 2. Global UX Principles

### 2.1 Never Break the Illusion

Users should **never see tokens, attempts, IP locks, or quotas** directly.

They only see:

* “Download”
* “Attempts remaining”
* “Upgrade to unlock more”

---

### 2.2 Predictability

* Same actions always behave the same
* No surprise failures
* Clear error messages (quota exhausted, expired link, etc.)

---

### 2.3 DJ-First, Not Tech-First

* DJs don’t think in “objects” or “tokens”
* They think in tracks, packs, fans, money

---

## 3. Information Architecture (High Level)

### 3.1 Public Pages

```
/                 → Homepage
/djs              → DJ discovery
/dj/{username}    → DJ storefront
/track/{slug}     → Track detail
/album/{slug}     → Album / ZIP page
```

---

### 3.2 Authenticated User Area

```
/account
  ├── purchases
  ├── subscriptions
  ├── downloads
  ├── points
  └── settings
```

---

### 3.3 DJ Dashboard

```
/dj/dashboard
  ├── overview
  ├── tracks
  ├── albums
  ├── fan-uploads
  ├── subscriptions
  ├── analytics
  ├── earnings
  └── settings
```

---

### 3.4 Admin Panel

```
/admin
  ├── dashboard
  ├── dj-approvals
  ├── users
  ├── content
  ├── payouts
  ├── abuse-dmca
  ├── analytics
  └── settings
```

---

## 4. Core UX Flows (Detailed)

---

### 4.1 Listener Purchase Flow (Track)

**Goal:** Buy → Download with zero confusion

**Steps**

1. Open track page
2. Watch YouTube preview
3. Click **Buy**
4. Login / signup if needed
5. Checkout
6. Success screen
7. Click **Download**
8. File downloads immediately

**UX Notes**

* “Attempts remaining” shown subtly
* No mention of tokens
* If expired → “Link expired, click again”

---

### 4.2 Subscription Download Flow

**Goal:** Make subscription feel powerful, not limited

**Steps**

1. User subscribes to DJ
2. Track shows **Download (Included)**
3. Click download
4. Backend checks quota
5. File delivered

**When quota exhausted**

* Button changes to:

  * “Upgrade plan”
  * OR “Buy this track”

---

### 4.3 Album / ZIP Flow

**Goal:** Emphasize premium value + protection

**UI Elements**

* Tracklist preview (non-downloadable)
* Higher price anchor
* “Limited downloads” note

**Flow**

1. Buy album
2. Download ZIP
3. Attempts decrease per download
4. Expired attempts → disabled button

---

### 4.4 Fan Uploads Flow (Super Tier)

**Goal:** Create exclusivity & FOMO

**UI Rules**

* Visible to everyone
* Locked icon for non-Super users
* “Super exclusive” badge

**Download**

* Only Super subscribers see download CTA
* Hard monthly limits
* Reset banner shown monthly

---

## 5. DJ Upload Experience

### 5.1 Track Upload UX

**Steps**

1. Upload audio
2. Auto-extract metadata
3. Set:

   * Title
   * Price
   * BPM / Genre
4. Add YouTube preview
5. Publish

**UX Guardrails**

* Cannot publish without preview
* Cannot exceed quota
* Clear errors before upload starts

---

### 5.2 Album / ZIP Upload UX

**Mode A — System ZIP**

* Upload multiple tracks
* Arrange order
* MixMint generates ZIP

**Mode B — Direct ZIP**

* Upload ZIP
* Provide metadata
* Tracklist required

**UX Safety**

* ZIP validation before publish
* Size & format checks
* Duplicate detection

---

## 6. DJ Analytics UX

**Dashboard Cards**

* Revenue (today / month / lifetime)
* Downloads
* Subscribers
* Top track

**Charts**

* Sales over time
* Subscription growth
* Track performance comparison

**Design Rule**

> Analytics should answer “what should I do next?” not just show numbers.

---

## 7. Admin UX Philosophy

### 7.1 Admin ≠ Power User

Admins:

* Act on alerts
* Review edge cases
* Don’t manage daily operations

---

### 7.2 Admin Dashboard Focus

* What’s broken?
* What needs approval?
* What’s risky?

**Top Widgets**

* Pending DJ approvals
* DMCA alerts
* Failed payouts
* Abuse flags

---

## 8. Error States & Messaging

### Examples

* ❌ “Download failed”

* ✅ “This link expired. Click download again.”

* ❌ “Unauthorized”

* ✅ “Please log in to continue.”

* ❌ “Quota exceeded”

* ✅ “Your plan limit is reached. Upgrade or buy this track.”

---

## 9. Accessibility & Responsiveness

* Mobile-first layouts
* Large tap targets
* Clear contrast
* Keyboard navigation
* No hidden critical actions

---

## 10. What This Design Explicitly Avoids

* Audio players
* Waveforms with playback
* Over-animated UI
* Dark patterns
* Confusing upgrade pressure

---

