
---

# — 🧠 TECHNICAL ARCHITECTURE & TECH STACK

**(Frontend, Backend, Storage, Security, Data Model)**

This document explains **how MixMint is built**, **why each choice exists**, and **how the pieces talk to each other**.

---

## 1. System Architecture (High Level)

```
Browser (User / DJ / Admin)
        ↓
Next.js App (Frontend + API routes)
        ↓
Access Validation Layer
(Auth • Ownership • Quotas • Tokens)
        ↓
Secure Download Proxy
        ↓
Cloudflare R2 (Private Storage)
```

**Key Idea:**
Files are **never accessed directly**. Everything flows through validation.

---

## 2. Frontend Stack

### Core

* **Next.js (App Router)**

  * SSR for SEO (DJ pages, tracks)
  * API routes for secure downloads
* **TypeScript**

  * Mandatory (security + sanity)
* **Tailwind CSS**

  * Fast iteration
  * Consistent design system

### UI Patterns

* Server Components for data-heavy pages
* Client Components only for:

  * Uploads
  * Checkout
  * Dashboards
* Optimistic UI for downloads & purchases

---

## 3. Backend Stack

### Authentication & Database

* **Supabase**

  * Auth (email + OAuth)
  * Postgres DB
  * Row Level Security (RLS)

**Important Design Rule**

> `profiles.id === auth.users.id` (single source of truth)

---

### Storage

* **Cloudflare R2**

  * Private buckets
  * No public access
  * Cheap, scalable, fast
* Accessed **only via server**

---

### Payments

* **Razorpay** (India-first)
* **Stripe** (global-ready)

Handled via:

* Webhooks
* Server-side verification
* Idempotency keys

---

## 4. Core Backend Concepts

### 4.1 Ownership Model

Ownership is **explicit**, never inferred.

**Sources of access**

* Purchase
* Active subscription quota
* Fan-upload entitlement

Each is checked independently.

---

### 4.2 Download Token System (Critical)

**Token Properties**

* `id`
* `user_id`
* `content_type` (track | album | fan)
* `content_id`
* `expires_at`
* `used_at`
* `ip_address`

**Rules**

* Generated per click
* Expires in 2–5 minutes
* One-time use
* IP locked on first download

---

### 4.3 Download Flow (Backend)

```
User clicks Download
        ↓
POST /api/download/init
        ↓
Validate:
- Auth
- Ownership OR quota
- Attempts remaining
        ↓
Create token (DB)
        ↓
Return short-lived URL
        ↓
GET /api/download/file?token=xyz
        ↓
Validate token again
        ↓
Stream file from R2
```

---

## 5. Database Design (Core Tables)

### 5.1 Users & Profiles

* `auth.users` (Supabase)
* `profiles`

  * id (PK, same as auth)
  * role (user | dj | admin)
  * status
  * metadata

---

### 5.2 Content Tables

* `tracks`
* `albums`
* `fan_uploads`

Common fields:

* `id`
* `dj_id`
* `price`
* `file_path`
* `attempt_limit`
* `created_at`

---

### 5.3 Purchases

* `purchases`

  * user_id
  * content_type
  * content_id
  * payment_id
  * created_at

---

### 5.4 Subscriptions

* `subscriptions`

  * user_id
  * dj_id
  * plan
  * started_at
  * expires_at

* `subscription_usage`

  * subscription_id
  * tracks_used
  * zips_used
  * fan_used
  * reset_at

---

### 5.5 Download Tracking

* `download_tokens`
* `download_attempts`

Used for:

* Abuse detection
* Rate limiting
* Auditing

---

## 6. Security Architecture

### 6.1 RLS (Row Level Security)

* Users can only see:

  * Their purchases
  * Their subscriptions
  * Their downloads
* DJs can only see:

  * Their own content
  * Their own earnings

Admins bypass via service role only.

---

### 6.2 Anti-Piracy Controls

* Tokenized downloads
* Attempt limits
* IP locking
* Device fingerprinting (future)
* Rate limiting per user & IP

---

### 6.3 File Metadata Injection

Every uploaded file embeds:

* DJ ID
* Timestamp
* MixMint platform ID

Used for:

* Ownership proof
* DMCA defense
* Leak tracing

---

## 7. Upload Architecture

### 7.1 Track Upload

```
Browser
 → Signed upload request
 → Server validates quota
 → Upload to R2
 → Metadata stored in DB
```

### 7.2 Album Upload

* System ZIP:

  * Upload tracks
  * Server zips
  * Upload ZIP
* Direct ZIP:

  * Validate contents
  * Store ZIP

---

## 8. Admin Architecture

Admin panel uses:

* Same frontend
* Separate route guard
* Service role DB access
* Audit logging on every action

---

## 9. Observability & Logs

* Download logs
* Payment logs
* Token usage logs
* Abuse flags
* Admin action logs

Essential for:

* Debugging
* Legal defense
* Trust

---

## 10. Why This Stack Works

* Supabase → fast auth + RLS
* Next.js → unified frontend + backend
* R2 → cheap, private, scalable
* Token system → core IP protection

This architecture is:

* Hard to pirate
* Easy to scale
* Friendly to DJs
* Cheap to operate early

---
