# 📦 DETAILED ENGINEERING HANDOFF DOCUMENT

**Project: MixMint**
**Audience:** New developer / replacement team / AI agent
**Status:** Production-grade foundation, feature-complete spec

---

## 1. What You Are Building (Read This First)

MixMint is **NOT**:

* a streaming platform
* a Spotify alternative
* a media player

MixMint **IS**:

* a **secure digital distribution system**
* for **DJ-owned downloadable content**
* with **hard anti-piracy enforcement**
* and **per-DJ subscription economics**

If you violate *any* of the core principles below, the product breaks.

---

## 2. Non-Negotiable Rules (If You Break These, Stop)

1. **No streaming — ever**
2. **No public file URLs**
3. **All downloads must be token-based**
4. **Every download must be validated server-side**
5. **Quotas are enforced strictly**
6. **Purchases override subscriptions**
7. **New click = new token (always)**

---

## 3. System Mental Model (How to Think About MixMint)

Think in **layers**:

```
UI
↓
Auth & Role Guard
↓
Access Validation (ownership / quota)
↓
Token Issuance
↓
Secure File Proxy
↓
Private Storage
```

No layer is allowed to skip another.

---

## 4. Authentication & Roles

### Roles

* `user` → buyer / fan
* `dj` → content owner
* `admin` → moderation & payouts

### Source of Truth

* Supabase Auth
* `profiles.id === auth.users.id`

Never duplicate auth state.

---

## 5. Content Rules (Very Important)

### Track

* One audio file
* Can be:

  * purchased
  * included in subscription
* Limited download attempts

### Album / ZIP

* Always paid
* Always higher protection
* One archive per purchase

### Fan Upload

* Single track only
* Super tier only
* Never purchasable
* Monthly capped

Never mix these concepts.

---

## 6. Download System (CORE IP)

### Token Lifecycle

1. User clicks **Download**
2. Server validates:

   * auth
   * ownership OR quota
   * attempts remaining
3. Token created in DB
4. Token expires in minutes
5. Token used once
6. Token invalid forever after use

### Why This Exists

* Stops link sharing
* Stops hotlinking
* Stops “download once → share everywhere”

If you feel tempted to simplify this, **don’t**.

---

## 7. Subscription Logic (Common Mistakes to Avoid)

* Subscriptions are **per DJ**
* Users can subscribe to many DJs
* Quotas reset monthly
* No rollover
* No unlimited plans
* Purchases always bypass quota

Never auto-download content on subscription start.

---

## 8. Payments & Money Flow

### Money Flow

```
User → Payment Gateway → MixMint
MixMint → DJ (minus commission)
```

### Rules

* Never trust frontend payment success
* Always verify webhooks
* All money state changes are server-only
* Refunds reverse entitlement

---

## 9. Admin Philosophy

Admins are **exception handlers**, not operators.

Admins should:

* Approve DJs
* Handle abuse
* Resolve disputes
* Release payouts

Admins should NOT:

* Manually manage content
* Bypass security rules
* Modify user entitlements arbitrarily

Everything must be logged.

---

## 10. Database Discipline

### Required Practices

* Use transactions for:

  * purchases
  * downloads
  * quota updates
* Never decrement quota without a successful token issue
* Never stream directly from storage
* Every destructive action must be reversible or logged

---

## 11. Logging & Auditing (Non-Optional)

You must log:

* Download attempts
* Token usage
* Payment webhooks
* Admin actions
* Abuse flags

This is required for:

* debugging
* DMCA defense
* dispute resolution
* trust

---

## 12. Scaling Expectations

The system is designed to scale by:

* stateless API routes
* cheap private storage (R2)
* short-lived tokens
* minimal cron jobs

You do **not** need:

* microservices
* message queues
* over-engineering

Yet.

---

## 13. What NOT to Build (Seriously)

Do NOT add:

* audio playback
* previews hosted by MixMint
* unlimited downloads
* shared folders
* DRM plugins
* blockchain / NFTs

They actively weaken the product.

---

## 14. How to Extend MixMint Safely

If adding features, they must:

* Respect token system
* Respect quotas
* Respect ownership
* Be auditable
* Be reversible

Good extensions:

* better analytics
* better discovery
* marketing tools
* branding features

Dangerous extensions:

* “just one preview”
* “temporary public link”
* “admin override download”

---

## 15. Final Instruction to Whoever Takes Over

> **If something feels annoying or strict — it’s probably intentional.**
> MixMint’s value is **control, not convenience**.

If a DJ loses control, MixMint fails.

---

