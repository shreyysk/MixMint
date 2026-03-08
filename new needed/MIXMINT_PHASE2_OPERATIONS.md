# 🎛️ MIXMINT — PHASE 2: OPERATIONS & TRUST
### *Build after Phase 1 is live and stable. First real users onboarded.*
### *Version: Final · March 2026*

---

## PHASE 2 SCOPE

```
Goal:         A platform that buyers and DJs trust deeply.
              Admin can operate it without manual intervention.
              Platform is legally protected. Revenue is optimised.

Prerequisites:
  → Phase 1 fully deployed and tested
  → At least 5 DJs onboarded
  → First real purchases completed
  → No critical bugs open from Phase 1

Includes:
  → Platform fixes 11–17 (SEO, analytics, invoices, etc.)
  → Improvements 07–10 (DJ directory, preview validation,
    platform health, waitlist)
  → Ad system (Google AdSense)
  → In-app notifications
  → Email unsubscribe management
  → Maintenance mode
  → Error pages
  → Pre-launch waitlist → launch email flow
  → DJ verified badge application process
  → DJ directory + collaboration requests
  → Dark pattern audit

Does NOT include:
  → Growth/acquisition features (Phase 3)
  → Nice-to-have polish (Phase 3)
```

---

## PHASE 2 BUILD ORDER

```
Step 1   Section C   Platform Fixes 11–17
         Fix 11:     Real-Time vs Cached Analytics
         Fix 12:     SEO, OG Tags & Sitemap
         Fix 13:     Download Insurance
         Fix 14:     Maintenance Mode UX
         Fix 15:     Security Page Copy
         Fix 16:     Anti-Scraping Layer
         Fix 17:     GST Invoice PDF Design
Step 2   Section D   Improvements 07–10
         Imp 07:     DJ Directory & Collab Requests
         Imp 08:     Preview URL Validation
         Imp 09:     Platform Health Dashboard
         Imp 10:     Waitlist → Launch Email Flow
Step 3   Section E   Infrastructure Gaps (High Priority)
         Gap 01:     Ad System (Google AdSense)
         Gap 09:     In-App Notification System
         Gap 11:     Email Unsubscribe Management
         Gap 12:     Custom Domain SEO
         Gap 13:     Buyer Profile Page
         Gap 14:     Changelog Page
         Gap 15:     Custom Error Pages
Step 4   Section D   Improvement 19 (Dark Pattern Audit)
Step 5   Re-run Section F QA on all new features
```

---


# ═══════════════════════════════════════════════════
# SECTION C — PLATFORM FIXES 11–17
# ═══════════════════════════════════════════════════
# FIX 11 — REAL-TIME VS CACHED ANALYTICS

## Which Data Needs to Be Real-Time vs Cached

```
REAL-TIME (never cache):
  - Kill switch status
  - Account freeze status
  - Active download token validity
  - Suspicious activity alerts
  - Maintenance mode status

NEAR-REAL-TIME (cache 5 minutes):
  - Pending payout amounts
  - Active refund requests
  - Report queue count

HOURLY CACHE:
  - DJ individual earnings (current month)
  - Platform commission total (this month)
  - Active DJ count

DAILY CACHE (refresh at midnight):
  - Lifetime platform revenue
  - All-time earnings per DJ
  - Investor report data
  - Top DJs by revenue
  - Storage usage totals
```

---

## Implementation with Django Cache

```python
from django.core.cache import cache
from django.utils import timezone

def get_platform_monthly_revenue():
    cache_key = f"platform_revenue_{timezone.now().strftime('%Y_%m')}"
    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    # Calculate from DB
    revenue = Purchase.objects.filter(
        created_at__month=timezone.now().month,
        created_at__year=timezone.now().year,
        status='active'
    ).aggregate(
        total=Sum('commission')
    )['total'] or 0

    # Cache for 1 hour
    cache.set(cache_key, revenue, 3600)
    return revenue


def get_dj_monthly_earnings(dj_id):
    cache_key = f"dj_earnings_{dj_id}_{timezone.now().strftime('%Y_%m')}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    earnings = calculate_dj_earnings(dj_id)
    cache.set(cache_key, earnings, 300)  # 5 min
    return earnings


def invalidate_dj_earnings_cache(dj_id):
    """Call this whenever a new purchase completes"""
    cache_key = f"dj_earnings_{dj_id}_{timezone.now().strftime('%Y_%m')}"
    cache.delete(cache_key)
```

---

## Admin Dashboard — Cache Status Indicator

Small indicator at bottom of admin dashboard:
```
Data freshness:
Revenue totals: updated 23 min ago  [Refresh]
DJ earnings:    updated 4 min ago
Storage:        updated 6h ago
```

---
---

# FIX 12 — SEO, OG TAGS & SITEMAP

## Open Graph Tags (Per Page)

```python
# Track detail page
def track_detail_og(track):
    return {
        'og:title': f"{track.title} — {track.dj_name} | MixMint",
        'og:description': (
            f"Buy and download '{track.title}' by {track.dj_name}. "
            f"₹{track.price} · {track.genre} · mixmint.site"
        ),
        'og:image': track.artwork_url,  # CDN URL of artwork
        'og:url': f"https://mixmint.site/track/{track.id}",
        'og:type': 'music.song',
        'og:site_name': 'MixMint',
        # WhatsApp / Twitter card
        'twitter:card': 'summary_large_image',
        'twitter:title': f"{track.title} — ₹{track.price}",
        'twitter:image': track.artwork_url,
    }

# DJ Storefront page
def dj_storefront_og(dj):
    return {
        'og:title': f"{dj.display_name} — DJ Storefront | MixMint",
        'og:description': (
            f"{dj.bio[:120]}... "
            f"{dj.track_count} tracks available on MixMint."
        ),
        'og:image': dj.avatar_url,
        'og:url': f"https://mixmint.site/dj/{dj.username}",
        'og:type': 'profile',
    }
```

---

## Dynamic Sitemap (`/sitemap.xml`)

```python
# sitemap.py
from django.contrib.sitemaps import Sitemap

class TrackSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Track.objects.filter(
            is_active=True,
            is_deleted=False,
            file_status='ready'
        )

    def lastmod(self, track):
        return track.updated_at

    def location(self, track):
        return f'/track/{track.id}'


class DJStorefrontSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return Profile.objects.filter(
            role='dj',
            store_paused=False
        )

    def location(self, dj):
        return f'/dj/{dj.username}'


SITEMAPS = {
    'tracks': TrackSitemap,
    'dj_storefronts': DJStorefrontSitemap,
}
```

---

## SEO Rules

```
Index:      Track pages, DJ storefront pages, Homepage, /pro, /security
No-index:   /checkout, /download, /library, /dj-panel, /admin
            (private or transactional pages — no SEO value)

Canonical:  Custom domain DJ pages should canonical to mixmint.site/dj/X
            (prevents duplicate content between custom domain + main domain)

robots.txt:
  User-agent: *
  Disallow: /admin/
  Disallow: /dj-panel/
  Disallow: /checkout/
  Disallow: /download/
  Disallow: /library/
  Allow: /
  Sitemap: https://mixmint.site/sitemap.xml
```

---
---

# FIX 13 — DOWNLOAD INSURANCE FULL SPEC

## What Insurance Is

A one-time add-on purchased per track/album that grants one additional free re-download, bypassing the 50% re-download fee and the 2-day lock.

---

## Rules

```
Available:      After 24 hours from original purchase
Price:          25% of original track price (admin-controlled %)
Covers:         1 additional download, no lock period required
Expires:        12 months from purchase
Not stackable:  Cannot buy insurance twice on same purchase
Not transferable: Bound to buyer's account
```

---

## UI — Track Page / Library

On track page (if >24h since purchase):
```
┌──────────────────────────────────────────────────────┐
│  🛡 Download Insurance  — ₹12                       │
│                                                      │
│  One free re-download, anytime within 12 months.   │
│  Skip the 2-day wait and 50% re-download fee.      │
│                                                      │
│  [Add Insurance — ₹12]                             │
└──────────────────────────────────────────────────────┘
```

---

## Admin Insurance Controls

```
Insurance rate:         [ 25 ]% of original price
Insurance enabled:      [  ON  ●────────  ]
Insurance expiry:       [ 12 ] months
```

---

## DB Schema

```sql
CREATE TABLE download_insurance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  purchase_id UUID REFERENCES purchases(id) UNIQUE,
  user_id UUID REFERENCES profiles(id),
  price_paid INTEGER,  -- in paise
  purchased_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  used BOOLEAN DEFAULT FALSE,
  used_at TIMESTAMPTZ
);
```

---
---

# FIX 14 — MAINTENANCE MODE UX

## What Users See During Maintenance

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│           [MixMint Logo]                                    │
│                                                              │
│        We're tuning the decks. 🎛️                          │
│                                                              │
│   MixMint is down for scheduled maintenance.               │
│   We'll be back shortly.                                    │
│                                                              │
│   [optional] Estimated back: 2:30 PM IST                   │
│                                                              │
│   Follow us for updates: @mixmint                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

- Full-page, centered, branded — not a generic 503
- Dark/light themed (respects system preference even on maintenance page)
- No nav, no links — just the message
- Estimated time optional — admin can leave blank if unknown

---

## Access Rules During Maintenance

```
Blocked:    All public pages, browse, track pages, checkout
            DJ dashboard
Allowed:    /admin (admin can still work during maintenance)
            Active download tokens already generated
            (don't kill in-progress downloads)
```

---

## Admin Maintenance Controls

```
┌──────────────────────────────────────────────────────────────┐
│  MAINTENANCE MODE                                            │
│                                                              │
│  [  OFF  ●──────────  ]  Currently: NORMAL                 │
│                                                              │
│  Maintenance message:                                        │
│  [ We're tuning the decks. Back shortly.          ]        │
│                                                              │
│  Estimated return time:  [  __:__ AM/PM IST  ]  (optional) │
│                                                              │
│  [Save & Enable Maintenance Mode]                           │
└──────────────────────────────────────────────────────────────┘
```

---
---

# FIX 15 — TRANSPARENCY / SECURITY PAGE COPY

## Full Page at `/security`

---

### Section 1 — How Your Download is Protected

> When you buy a track on MixMint, your file is never stored at a public URL. It lives in a private vault (Cloudflare R2) with no direct access — not even we can share a link that works twice.
>
> Every download goes through a secure token — a one-time key that expires in minutes, bound to your device and IP address. Once used, the token is dead. Nobody else can use it, not even you.

---

### Section 2 — What "Byte Verification" Means

> Every download is verified before it's marked complete. We check that 100% of the file reached your device and that the file's fingerprint (checksum) matches the original. If anything went wrong — connection dropped, file corrupted — it's not marked as your download. You can retry or request a refund.

---

### Section 3 — Device Locking

> After a successful download, the file is locked to your device and IP for 48 hours. This protects artists from the same file being downloaded across multiple devices immediately. After 48 hours, you can re-download for 50% of the original price — or buy Download Insurance for unlimited peace of mind.

---

### Section 4 — Attempt Limits

> Each purchase gets 3 download attempts per IP address. We show a warning when you're on your final attempt. This isn't about punishing buyers — it's about ensuring that files stay in the hands of people who paid for them, not passed around as shared links.

---

### Section 5 — Your Files Are Watermarked

> Every file sold through MixMint has platform metadata embedded — the DJ's ID, a timestamp, and an anti-resale notice. This helps protect artists and creates a traceable record if files are redistributed without permission.

---

### Section 6 — Content Responsibility

> MixMint is a marketplace. Every track and album is uploaded independently by the DJ who sells it. DJs are legally responsible for the content they upload, including having the rights to sell it. MixMint responds to valid copyright notices promptly. See our Content Policy for how to file a report.

---

### Footer of Security Page

> Questions about security or a specific concern? Contact us at security@mixmint.site

---
---

# FIX 16 — ANTI-SCRAPING LAYER

## Cloudflare Free Tier Rules (Set in Cloudflare Dashboard)

```
Rule 1: Rate limit search API
  Path: /api/search/*
  Limit: 30 requests/minute per IP
  Action: Block for 10 minutes

Rule 2: Rate limit track listings
  Path: /api/tracks/*
  Limit: 60 requests/minute per IP
  Action: Challenge (CAPTCHA)

Rule 3: Block headless browsers
  Expression: (http.user_agent contains "HeadlessChrome")
              OR (http.user_agent contains "Puppeteer")
              OR (http.user_agent eq "")
  Action: Block

Rule 4: Bot score threshold
  Expression: cf.bot_management.score < 30
  Action: Challenge
  (Requires Cloudflare Bot Management — free tier has basic version)
```

---

## Django-Level Honeypot

```python
# In track listing API — add invisible field check
def track_list_api(request):
    # Honeypot: legitimate browsers never send this parameter
    # Scrapers that blindly send all form fields will hit this
    if request.GET.get('_bot_trap'):
        # Log the IP, add to suspicious list
        flag_suspicious_ip(get_client_ip(request))
        # Return fake empty results (don't block — don't tip them off)
        return JsonResponse({'results': [], 'total': 0})

    # Normal processing...
```

---

## User-Agent Validation

```python
BLOCKED_USER_AGENTS = [
    'python-requests', 'curl', 'wget', 'scrapy',
    'Go-http-client', 'Java/', 'libwww'
]

def check_user_agent(request):
    ua = request.META.get('HTTP_USER_AGENT', '')
    for blocked in BLOCKED_USER_AGENTS:
        if blocked.lower() in ua.lower():
            return False
    return True
```

---
---

# FIX 17 — GST INVOICE PDF DESIGN

## Layout Specification

```
Page size: A4
Margins: 20mm all sides
Font: Satoshi (body) + DM Mono (numbers)
Colors: Match MixMint brand — dark theme invoice
```

---

## Invoice Structure

```
┌──────────────────────────────────────────────────────────────┐
│  [MixMint Logo]                    TAX INVOICE              │
│  mixmint.site                      Invoice #: MM-2026-00142 │
│  support@mixmint.site              Date: 06 Mar 2026        │
├──────────────────────────────────────────────────────────────┤
│  BILLED TO                         SOLD BY                  │
│  Buyer Name                        DJ Display Name          │
│  buyer@email.com                   (Independent Artist)     │
│  [City, State]                     Platform: MixMint        │
├──────────────────────────────────────────────────────────────┤
│  ITEM                                                        │
│  Track: [Track Title]                                       │
│  Genre: [Genre] · Year: [Year]                              │
│  Sold by: [DJ Name] via MixMint                            │
├──────────────────────────────────────────────────────────────┤
│  Base Price                              ₹  XX.XX           │
│  Platform Service Charge                 ₹   X.XX           │
│  GST @ 18% (if applicable)              ₹   X.XX           │
│                               ─────────────────────         │
│                               TOTAL      ₹  XX.XX           │
├──────────────────────────────────────────────────────────────┤
│  Payment Method: Razorpay / PhonePe                         │
│  Transaction ID: [gateway_payment_id]                       │
│  Payment Status: PAID ✓                                     │
├──────────────────────────────────────────────────────────────┤
│  This is a computer-generated invoice. No signature needed. │
│                                                              │
│  Content sold by independent DJ. MixMint is not            │
│  responsible for content licensing.                         │
│  Anti-resale: Personal use only. Non-transferable.         │
└──────────────────────────────────────────────────────────────┘
```

---

## PDF Generation

```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

def generate_invoice_pdf(purchase_id):
    purchase = Purchase.objects.select_related(
        'buyer', 'dj', 'track'
    ).get(id=purchase_id)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    # Build elements array with all invoice sections
    elements = build_invoice_elements(purchase)
    doc.build(elements)

    # Store in R2 under private invoices prefix
    pdf_bytes = buffer.getvalue()
    r2_key = f"invoices/{purchase.id}.pdf"
    upload_to_r2(pdf_bytes, r2_key, content_type='application/pdf')

    # Store reference on purchase
    Purchase.objects.filter(id=purchase_id).update(
        invoice_r2_key=r2_key
    )

    return r2_key
```

---

## When GST Is Disabled

- Invoice still generated
- GST line: not shown at all (not "₹0" — simply absent)
- Base price = what buyer paid (full amount)
- Note at bottom: *"GST not applicable — platform below registration threshold"*

---

*End of MixMint All Fixes Prompt*
*17 systems. Zero gaps. Build-ready.*

*Fix 01: Refund Engine · Fix 02: Custom Domains · Fix 03: Metadata Injection*
*Fix 04: Search Algorithm · Fix 05: Collab Edge Cases · Fix 06: 2FA*
*Fix 07: DJ Onboarding · Fix 08: Content Reporting · Fix 09: Star Ratings*
*Fix 10: Payout Details · Fix 11: Analytics Caching · Fix 12: SEO & OG Tags*
*Fix 13: Download Insurance · Fix 14: Maintenance Mode · Fix 15: Security Page*
*Fix 16: Anti-Scraping · Fix 17: Invoice PDF*

---


# ═══════════════════════════════════════════════════
# SECTION D — IMPROVEMENTS 07–10
# ═══════════════════════════════════════════════════
# IMPROVEMENT 07 — DJ DIRECTORY & COLLABORATION REQUESTS

## DJ Directory Page (`/djs`)

```
┌──────────────────────────────────────────────────────────────┐
│  DJ DIRECTORY                                               │
│                                                              │
│  [Search DJs by name or genre...]                          │
│                                                              │
│  Filter by genre: [All] [House] [Techno] [Bollywood] [EDM] │
│  Sort: [Newest] [Most Tracks] [Top Sellers] [Verified]     │
│                                                              │
│  [DJ Card Grid — same as homepage DJ cards]                │
└──────────────────────────────────────────────────────────────┘
```

- Public page — no login required to browse
- Each DJ card links to their storefront
- Verified badge shown prominently

---

## Collaboration Request System

### Sending a Request (DJ Dashboard → Collaborations → Find DJs)

```
┌──────────────────────────────────────────────────────────────┐
│  Send Collaboration Request                                  │
│                                                              │
│  To DJ: [search by name/username]                           │
│                                                              │
│  Track: ○ Existing track  ● New track (not uploaded yet)   │
│  If existing: [select from dropdown]                        │
│                                                              │
│  Message: [optional, max 300 chars]                         │
│  e.g. "Hey, want to collab on a house set?"                │
│                                                              │
│  Proposed split: You [ 70 ]%  ·  Them [ 30 ]%             │
│  (They can counter-propose when responding)                 │
│                                                              │
│  [Send Request]                                             │
└──────────────────────────────────────────────────────────────┘
```

---

### Receiving a Request (DJ Dashboard → Collaborations → Inbox)

```
┌──────────────────────────────────────────────────────────────┐
│  Collaboration Requests (2 pending)                         │
│                                                              │
│  FROM: DJ Rohit                               2 days ago   │
│  Track: New track (unnamed)                                 │
│  Proposed split: 70% Rohit / 30% You                       │
│  Message: "Want to work on a Bollywood remix together?"    │
│                                                              │
│  Your split counter: [ 30 ]% (or accept their proposal)   │
│                                                              │
│  [Accept] [Counter-Propose] [Decline]                      │
└──────────────────────────────────────────────────────────────┘
```

---

## DB Schema

```sql
CREATE TABLE collab_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_dj_id UUID REFERENCES profiles(id),
  to_dj_id UUID REFERENCES profiles(id),
  track_id UUID REFERENCES tracks(id) NULL,
  message TEXT,
  proposed_split_from INTEGER,   -- % for sender
  proposed_split_to INTEGER,     -- % for recipient
  counter_split_from INTEGER,    -- if recipient counters
  counter_split_to INTEGER,
  status VARCHAR(20) DEFAULT 'pending',
    -- 'pending' | 'accepted' | 'declined' | 'countered' | 'expired'
  expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  responded_at TIMESTAMPTZ
);
```

---
---

# IMPROVEMENT 08 — PREVIEW URL VALIDATION

## On Upload — Immediate Validation

```python
import requests
from urllib.parse import urlparse, parse_qs
import re

def validate_youtube_url(url):
    """
    Validates that:
    1. URL is a valid YouTube URL
    2. Video exists (not 404)
    3. Video is public (not private/unlisted)
    """
    # Extract video ID
    patterns = [
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})'
    ]
    video_id = None
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break

    if not video_id:
        return False, "Not a valid YouTube URL"

    # Check via YouTube oEmbed (free, no API key)
    oembed_url = (
        f"https://www.youtube.com/oembed"
        f"?url=https://www.youtube.com/watch?v={video_id}"
        f"&format=json"
    )
    try:
        resp = requests.get(oembed_url, timeout=5)
        if resp.status_code == 200:
            return True, None
        elif resp.status_code == 401:
            return False, "Video is private or age-restricted"
        elif resp.status_code == 404:
            return False, "Video not found or has been deleted"
        else:
            return False, "Could not verify video"
    except requests.RequestException:
        return False, "Could not reach YouTube to verify"


def validate_instagram_url(url):
    """Basic format validation for Instagram Reels"""
    pattern = r'instagram\.com/(reel|p)/([a-zA-Z0-9_-]+)'
    if re.search(pattern, url):
        return True, None
    return False, "Not a valid Instagram Reel URL"
```

---

## Periodic Active Preview Checking

```python
# Cron job — runs daily
def check_all_active_previews():
    tracks = Track.objects.filter(
        is_active=True,
        is_deleted=False,
        preview_type='youtube'
    )
    broken = []
    for track in tracks:
        valid, error = validate_youtube_url(track.youtube_url)
        if not valid:
            broken.append({
                'track_id': track.id,
                'dj_id': track.dj_id,
                'error': error,
                'url': track.youtube_url
            })
            # Flag track
            track.preview_broken = True
            track.preview_error = error
            track.save()
            # Notify DJ
            send_broken_preview_email(track.dj_id, track, error)

    if broken:
        send_admin_broken_previews_report(broken)
```

---

## UI States for Broken Preview

On track detail page when preview is broken:
```
┌──────────────────────────────────────────────────────┐
│  Preview currently unavailable                       │
│  The DJ has been notified.                          │
└──────────────────────────────────────────────────────┘
```

In DJ Dashboard → My Tracks:
```
⚠ Preview broken — [Update Preview URL]
```
Amber warning badge on affected track row.

---

## DB Schema

```sql
ALTER TABLE tracks
  ADD COLUMN preview_broken BOOLEAN DEFAULT FALSE,
  ADD COLUMN preview_error VARCHAR(200),
  ADD COLUMN preview_last_checked TIMESTAMPTZ;
```

---
---

# IMPROVEMENT 09 — PLATFORM HEALTH DASHBOARD

## Location: Admin → Platform Health (new section)

---

## Metrics Tracked

```
┌──────────────────────────────────────────────────────────────┐
│  PLATFORM HEALTH — Last 7 Days                             │
│                                                              │
│  Downloads                                                  │
│  Successful rate:     94.2%  ●●●●●●●●●○  ← green if >90%  │
│  Failed rate:          5.8%                                 │
│  Token expiry rate:    2.1%  (tokens unused before expiry) │
│  Avg download speed:  3.2 MB/s                             │
│                                                              │
│  Payments                                                   │
│  Success rate:        97.8%  ●●●●●●●●●●                   │
│  Failed rate:          2.2%                                 │
│  Chargeback rate:      0.3%  ← amber if >1%, red if >2%   │
│  Avg checkout time:    45s                                  │
│                                                              │
│  Platform                                                   │
│  Avg API response:    180ms  ← green if <300ms             │
│  Error rate (5xx):    0.02%                                │
│  Uptime (30 days):   99.94%                                │
│  Storage growth:      +4.2 GB this week                    │
│  Storage cost (est):  ₹1,240/month at this rate           │
│                                                              │
│  Users                                                      │
│  New signups (7d):    34                                    │
│  New DJ applications: 6                                     │
│  Active buyers (7d):  142                                   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Alert Thresholds (Admin-Configurable)

```
┌──────────────────────────────────────────────────────────────┐
│  HEALTH ALERT THRESHOLDS                                    │
│                                                              │
│  Download failure rate > [ 10 ]% → Email admin            │
│  Payment failure rate  > [  5 ]% → Email admin            │
│  Chargeback rate       > [  1 ]% → Email + SMS admin      │
│  API response time     > [500 ]ms → Email admin            │
│  Storage growth        > [ 10 ]GB/week → Email admin      │
│  Error rate (5xx)      > [  1 ]% → Email + SMS admin      │
│                                                              │
│  [Save Thresholds]                                         │
└──────────────────────────────────────────────────────────────┘
```

---

## Implementation (Metrics Collection)

```python
# metrics.py — called after each key event

def record_download_event(success, failure_reason=None, speed_mbps=None):
    DownloadMetric.objects.create(
        success=success,
        failure_reason=failure_reason,
        speed_mbps=speed_mbps,
        recorded_at=timezone.now()
    )

def record_payment_event(success, gateway, failure_reason=None):
    PaymentMetric.objects.create(
        success=success,
        gateway=gateway,
        failure_reason=failure_reason,
        recorded_at=timezone.now()
    )

# Dashboard query (cached hourly)
def get_health_metrics(days=7):
    since = timezone.now() - timedelta(days=days)

    downloads = DownloadMetric.objects.filter(recorded_at__gte=since)
    total = downloads.count()
    successful = downloads.filter(success=True).count()

    return {
        'download_success_rate': (successful / total * 100) if total else 0,
        'avg_speed_mbps': downloads.filter(
            success=True
        ).aggregate(avg=Avg('speed_mbps'))['avg'],
        # ... etc
    }
```

---
---

# IMPROVEMENT 10 — WAITLIST / PRE-LAUNCH EMAIL CAPTURE

## Waitlist Page (`/early-access` or `/waitlist`)

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  MixMint is launching soon.                                │
│                                                              │
│  India's first secure DJ music marketplace.                │
│  Buy. Own. Download. No streaming. No subscriptions.       │
│                                                              │
│  ─── For DJs ─────────────────────────────────────         │
│  Sell your music. Keep 90%. Device-locked files.          │
│  No Telegram. No Google Drive. Real revenue.              │
│                                                              │
│  ─── For Buyers ───────────────────────────────────        │
│  Own DJ music. Verified files. Secure downloads.          │
│                                                              │
│  Get notified at launch:                                   │
│                                                              │
│  [Email address              ]                             │
│  I am a:  ● DJ   ○ Music Buyer                            │
│  [Notify Me at Launch]                                     │
│                                                              │
│  [X] DJs signed up already  (shows count once >10)        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Launch Email Sequence

```
On signup:
  Subject: "You're on the MixMint waitlist ⚡"
  Content: What MixMint is, what to expect, approximate launch timeline

If DJ signup:
  Subject: "MixMint DJ early access — what you need to know"
  Content: Commission rates, storage, how uploads work, what to prepare

On launch day:
  Subject: "MixMint is live — you're in ⚡"
  Content: Direct link to platform, special launch offer details

  For DJs: Direct link to DJ application form
  For Buyers: Direct link to browse page
```

---

## Admin Waitlist Dashboard (Admin → Growth → Waitlist)

```
┌──────────────────────────────────────────────────────────────┐
│  WAITLIST                                                    │
│                                                              │
│  Total signups:     234                                      │
│  DJs:               89  (38%)                               │
│  Buyers:           145  (62%)                               │
│                                                              │
│  This week:        +34                                      │
│  Growth rate:      +17% week-over-week                      │
│                                                              │
│  [Export CSV]  [Send Announcement]  [Send Launch Email]    │
└──────────────────────────────────────────────────────────────┘
```

---

## DB Schema

```sql
CREATE TABLE waitlist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  role VARCHAR(10),  -- 'dj' | 'buyer'
  source VARCHAR(50),  -- 'organic' | 'instagram' | 'referral' | etc
  notified_launch BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

*End of Part 1 — Improvements 01–10*
*Dispute Resolution · Account Deletion · Fraud Detection · TDS Compliance*
*Session Management · Verified Badge · DJ Directory · Preview Validation*
*Platform Health · Waitlist System*

---

# 🚀 MIXMINT — IMPROVEMENTS PROMPT PART 2 (fixes 11–20)
### *Medium value, growth, and polish. Build-ready specifications.*

---


# ═══════════════════════════════════════════════════
# SECTION E — HIGH PRIORITY GAPS
# ═══════════════════════════════════════════════════
# GAP 01 — AD SYSTEM (COMPLETE SPEC)

## Architecture Decision

Use **Google AdSense** for launch — lowest friction, no direct advertiser relationships needed, auto-fills inventory. Switch to programmatic/direct later when traffic justifies it.

```
Ad Network:        Google AdSense (launch)
DJ Revenue Share:  15% of ad revenue attributed to their content
Attribution:       Per-page impression tracking by DJ ID
Ad Blocker:        Graceful fallback — no broken layouts
Pro DJs:           Ads hidden from DJ's own logged-in view only
                   Buyers always see ads regardless of DJ plan
```

---

## Ad Placement Map (Where Ads Appear)

```
Page                    Placement               Size
─────────────────────────────────────────────────────────────────
Track Detail            Below description        728×90 leaderboard
                        (above buy button)       or 320×50 mobile

DJ Storefront           Below DJ header          728×90
                        (above track grid)

Search Results          After row 3 of results   Native/responsive

Download Page           Below download container 728×90 static ONLY
                        (NEVER autoplay/video)

Homepage                Below "New Releases"     300×250 rectangle
                        section

DJ Storefront           Sidebar (desktop only)   300×600 half page
(Standard DJs)
```

**NEVER show ads:**
- Inside checkout flow
- On the download progress bar
- On admin pages
- On DJ dashboard pages
- In auth modals
- As popups or interstitials anywhere

---

## Ad Revenue Attribution Per DJ

Every ad impression on a DJ's content is tracked and credited at 15%:

```python
# middleware/ad_tracking.py

def track_ad_impression(request, dj_id, page_type, ad_slot):
    """
    Called when a page with DJ content loads.
    Records impression for later revenue attribution.
    """
    AdImpression.objects.create(
        dj_id=dj_id,
        page_type=page_type,        # 'track' | 'storefront' | 'search'
        ad_slot=ad_slot,            # 'leaderboard' | 'rectangle' | 'sidebar'
        ip_hash=hash_ip(get_client_ip(request)),  # hashed — no PII
        user_agent_hash=hash(request.META.get('HTTP_USER_AGENT', '')),
        session_id=request.session.session_key,
        recorded_at=timezone.now()
    )
```

---

## Ad Revenue Calculation (Weekly Cron)

```python
# AdSense doesn't give per-impression revenue in real time.
# You get total weekly revenue from AdSense dashboard.
# Distribute proportionally based on impression share.

def distribute_ad_revenue_weekly():
    """
    Run every Monday — calculates last week's ad revenue per DJ.
    Admin inputs total AdSense revenue for the week.
    System distributes by impression share.
    """
    week_start = get_last_week_start()
    week_end = get_last_week_end()

    total_impressions = AdImpression.objects.filter(
        recorded_at__range=(week_start, week_end)
    ).count()

    if total_impressions == 0:
        return

    # Group by DJ
    dj_impressions = AdImpression.objects.filter(
        recorded_at__range=(week_start, week_end),
        dj_id__isnull=False
    ).values('dj_id').annotate(count=Count('id'))

    # Admin inputs total AdSense revenue for the week
    total_adsense_revenue = get_admin_input_adsense_revenue(week_start)
    if not total_adsense_revenue:
        return  # Admin hasn't entered revenue yet — skip

    # Each DJ gets 15% of their proportional share
    for entry in dj_impressions:
        dj_share = (entry['count'] / total_impressions) * total_adsense_revenue
        dj_revenue = dj_share * Decimal('0.15')  # 15% to DJ

        if dj_revenue > 0:
            DJWallet.objects.filter(dj_id=entry['dj_id']).update(
                ad_revenue_pending=F('ad_revenue_pending') + dj_revenue,
                ad_revenue_total=F('ad_revenue_total') + dj_revenue
            )

            AdRevenueRecord.objects.create(
                dj_id=entry['dj_id'],
                week_start=week_start,
                impressions=entry['count'],
                platform_revenue=float(dj_share),
                dj_revenue=float(dj_revenue),
                impression_share=(entry['count'] / total_impressions * 100)
            )
```

---

## Admin — Ad Revenue Input Panel

```
Admin → Revenue Intelligence → Ad Revenue

┌──────────────────────────────────────────────────────────────┐
│  WEEKLY AD REVENUE ENTRY                                     │
│                                                              │
│  Week: 24 Feb – 02 Mar 2026                                 │
│                                                              │
│  Total AdSense revenue this week:                           │
│  ₹ [_________]  [Calculate & Distribute]                   │
│                                                              │
│  Preview distribution:                                      │
│  DJ Rohit:   12,450 impressions (34%)  →  ₹X to DJ        │
│  DJ Priya:    8,230 impressions (22%)  →  ₹X to DJ        │
│  ...                                                        │
│                                                              │
│  Platform keeps: 85% = ₹X                                  │
│  Total DJ share: 15% = ₹X                                  │
│                                                              │
│  [Confirm & Credit DJ Wallets]                             │
└──────────────────────────────────────────────────────────────┘
```

---

## Pro DJ — Ad Reduction Implementation

```python
# In template context / API response

def get_ad_config(request, dj_id):
    """
    Returns whether ads should be shown.
    Pro DJs don't see ads on their OWN storefront when logged in.
    Everyone else sees ads.
    """
    viewing_own_store = (
        request.user.is_authenticated and
        str(request.user.id) == str(dj_id)
    )
    dj_is_pro = Profile.objects.get(id=dj_id).is_pro_dj

    hide_ads = viewing_own_store and dj_is_pro

    return {
        'show_ads': not hide_ads,
        'ad_slots': get_active_ad_slots() if not hide_ads else []
    }
```

---

## Ad Blocker Handling

```javascript
// detect-adblocker.js
// Run on page load — if ad blocker detected, remove ad containers
// gracefully (no broken boxes, no "please disable" nagging)

async function detectAdBlocker() {
  try {
    // Try to fetch a known ad script path
    await fetch('https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js', {
      method: 'HEAD',
      mode: 'no-cors'
    });
    return false; // Not blocked
  } catch {
    return true; // Blocked
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const adBlocked = await detectAdBlocker();
  if (adBlocked) {
    // Remove ad containers — don't show empty boxes
    document.querySelectorAll('.ad-container').forEach(el => {
      el.style.display = 'none';
    });
    // Do NOT show "please disable ad blocker" message
    // It damages trust and doesn't work
  }
});
```

---

## DB Schema

```sql
CREATE TABLE ad_impressions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dj_id UUID REFERENCES profiles(id),
  page_type VARCHAR(20),
  ad_slot VARCHAR(30),
  ip_hash VARCHAR(64),
  session_id VARCHAR(64),
  recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ad_revenue_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dj_id UUID REFERENCES profiles(id),
  week_start DATE,
  impressions INTEGER,
  platform_revenue DECIMAL(10,2),
  dj_revenue DECIMAL(10,2),
  impression_share DECIMAL(5,2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(dj_id, week_start)
);

ALTER TABLE dj_wallet
  ADD COLUMN ad_revenue_pending DECIMAL(10,2) DEFAULT 0,
  ADD COLUMN ad_revenue_total DECIMAL(10,2) DEFAULT 0;
```

---
---

# GAP 09 — IN-APP NOTIFICATION SYSTEM

## Notification Types

```
Type                        For     Trigger
──────────────────────────────────────────────────────────────────
purchase_received           DJ      Buyer completes purchase
track_approved              DJ      Admin approves uploaded track
track_rejected              DJ      Admin rejects track
dispute_opened              DJ      Buyer opens dispute on their track
dispute_resolved            Both    Admin makes decision
payout_processed            DJ      Weekly payout sent
collab_request_received     DJ      Another DJ sends collab request
collab_request_accepted     DJ      Their collab request accepted
application_approved        User    DJ application approved
download_complete           Buyer   Download verified 100%
pro_trial_ending            DJ      2 days left on Pro trial
storage_warning             DJ      Storage at 80% of quota
```

---

## Notification Bell UI

In navbar, right side (logged-in users only):

```
🔔 3   ← bell icon with unread count badge
```

Clicking opens dropdown:

```
┌──────────────────────────────────────────────────────────┐
│  Notifications                         [Mark all read]  │
│  ─────────────────────────────────────────────────────  │
│  🛒  New purchase — "Deep Blue"           2 min ago  ●  │
│      Ravi bought your track for ₹49                     │
│                                                          │
│  ✓   Track approved — "Sunset Mix"        1 hr ago   ●  │
│      Your track is now live on MixMint                  │
│                                                          │
│  ⚡  Pro trial ending in 2 days           3 hrs ago      │
│      Add payment to continue                            │
│                                                          │
│  [View All Notifications →]                             │
└──────────────────────────────────────────────────────────┘
```

- Max 5 in dropdown, `View All` links to full notifications page
- Unread: left dot indicator + slightly elevated background
- Clicking notification marks as read + navigates to relevant page
- Bell badge disappears when all read

---

## Real-Time Updates (Supabase Realtime)

```javascript
// notifications.js — runs after login

import { supabase } from './supabase-client'

function subscribeToNotifications(userId) {
  const channel = supabase
    .channel(`notifications:${userId}`)
    .on(
      'postgres_changes',
      {
        event: 'INSERT',
        schema: 'public',
        table: 'notifications',
        filter: `user_id=eq.${userId}`
      },
      (payload) => {
        const notification = payload.new
        // Update bell badge count
        incrementNotificationBadge()
        // Show toast for important ones
        if (notification.priority === 'high') {
          showToast(notification.title, notification.body)
        }
      }
    )
    .subscribe()

  return channel  // Store to unsubscribe on logout
}
```

---

## Creating Notifications (Django)

```python
def create_notification(user_id, notif_type, title, body,
                        action_url=None, priority='normal'):
    Notification.objects.create(
        user_id=user_id,
        type=notif_type,
        title=title,
        body=body,
        action_url=action_url,
        priority=priority,  # 'normal' | 'high'
        is_read=False
    )
    # Supabase Realtime picks this up automatically
    # and pushes to subscribed frontend

# Example usage after purchase:
def on_purchase_complete(purchase):
    create_notification(
        user_id=purchase.dj_id,
        notif_type='purchase_received',
        title='New purchase',
        body=f"{purchase.buyer_name} bought \"{purchase.track_title}\" for ₹{purchase.display_price}",
        action_url=f"/dj-panel/earnings",
        priority='high'
    )
```

---

## DB Schema

```sql
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  type VARCHAR(50),
  title VARCHAR(100),
  body VARCHAR(300),
  action_url VARCHAR(500),
  priority VARCHAR(10) DEFAULT 'normal',
  is_read BOOLEAN DEFAULT FALSE,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX notifications_user_unread
  ON notifications(user_id, is_read)
  WHERE is_read = FALSE;

-- Enable Supabase Realtime on this table
-- In Supabase Dashboard: Database → Replication → notifications → enable
```

---
---

# GAP 11 — EMAIL UNSUBSCRIBE MANAGEMENT

## Email Categories (Different Unsubscribe Rules)

```
Category              Can Unsubscribe?   Notes
──────────────────────────────────────────────────────────────────
Transactional         NO                 Purchase receipts, invoices,
                                         download confirmations,
                                         refund decisions, security alerts
                                         Legal obligation to send

Account               NO                 Password reset, email verification,
                                         2FA alerts, account frozen

Operational           YES                Payout processed, track approved,
                                         dispute updates, TDS certificates

Marketing/Updates     YES                New features, changelog,
                                         platform announcements

DJ Weekly Summary     YES                Weekly earnings digest

Pro/Subscription      YES (partial)      Trial reminders, renewal notices
                                         (can delay but not fully disable)
```

---

## Unsubscribe Implementation (Resend)

```python
# Resend has built-in contact suppression
# Use their contacts API to manage preferences

import resend

resend.api_key = settings.RESEND_API_KEY

def create_resend_contact(user_id, email, role):
    """Create contact in Resend with default preferences"""
    resend.Contacts.create({
        "email": email,
        "unsubscribed": False,  # Subscribed by default
        "first_name": "",
        "audience_id": settings.RESEND_AUDIENCE_ID
    })

    # Store preferences locally too
    EmailPreferences.objects.create(
        user_id=user_id,
        email=email,
        operational_emails=True,
        marketing_emails=True,
        weekly_summary=True if role == 'dj' else False,
        pro_reminders=True
    )


def send_email_with_prefs(user_id, email_type, **kwargs):
    """
    Check preferences before sending.
    Always sends transactional/account emails.
    Checks opt-in for others.
    """
    ALWAYS_SEND = ['transactional', 'account', 'security']

    if email_type in ALWAYS_SEND:
        send_email(**kwargs)
        return

    prefs = EmailPreferences.objects.get(user_id=user_id)

    should_send = {
        'operational': prefs.operational_emails,
        'marketing': prefs.marketing_emails,
        'weekly_summary': prefs.weekly_summary,
        'pro_reminder': prefs.pro_reminders
    }.get(email_type, True)

    if should_send:
        send_email(**kwargs)
```

---

## One-Click Unsubscribe in Every Email

Every non-transactional email must include:

```html
<!-- Email footer -->
<p style="font-size:12px; color:#666;">
  You're receiving this because you have a MixMint account.
  <a href="https://mixmint.site/email/unsubscribe/?token={unsubscribe_token}&type={email_type}">
    Unsubscribe from these emails
  </a>
  ·
  <a href="https://mixmint.site/settings/notifications">
    Manage all email preferences
  </a>
</p>
```

---

## Unsubscribe Token Generation

```python
import hashlib
import hmac

def generate_unsubscribe_token(user_id, email_type):
    """
    Signed token — proves user owns the email without requiring login
    """
    message = f"{user_id}:{email_type}"
    token = hmac.new(
        settings.UNSUBSCRIBE_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{user_id}:{email_type}:{token}"


def process_unsubscribe(token_string):
    try:
        user_id, email_type, token = token_string.split(':')
        expected = generate_unsubscribe_token(user_id, email_type)

        if not hmac.compare_digest(token_string, expected):
            raise ValueError("Invalid token")

        # Update preference
        EmailPreferences.objects.filter(user_id=user_id).update(
            **{f"{email_type}_emails": False}
        )

        return True, email_type
    except Exception:
        return False, None
```

---

## Email Preferences Page (Settings → Notifications)

```
┌──────────────────────────────────────────────────────────────┐
│  Email Preferences                                          │
│                                                              │
│  ALWAYS SENT (cannot disable):                             │
│  · Purchase receipts and invoices                          │
│  · Security alerts                                         │
│  · Download confirmations                                  │
│  · Account and password emails                             │
│                                                              │
│  YOU CAN CONTROL:                                           │
│  [✓] Payout notifications        [ON ●────]               │
│  [✓] Track approval updates      [ON ●────]               │
│  [✓] Dispute updates             [ON ●────]               │
│  [✓] Platform announcements      [ON ●────]               │
│  [✓] Weekly earnings summary     [ON ●────]  (DJs only)   │
│  [✓] Pro plan reminders          [ON ●────]  (Pro DJs)    │
│                                                              │
│  [Save Preferences]                                         │
└──────────────────────────────────────────────────────────────┘
```

---

## DB Schema

```sql
CREATE TABLE email_preferences (
  user_id UUID PRIMARY KEY REFERENCES profiles(id),
  operational_emails BOOLEAN DEFAULT TRUE,
  marketing_emails BOOLEAN DEFAULT TRUE,
  weekly_summary BOOLEAN DEFAULT TRUE,
  pro_reminders BOOLEAN DEFAULT TRUE,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---
---

# GAP 12 — CUSTOM DOMAIN SEO DECISION

## The Decision

**Chosen approach: Canonical to MixMint + Separate OG**

```
Custom domain gets:
  - Its own OG tags (DJ's branding in shares)
  - Its own page title
  - Canonical pointing to mixmint.site/dj/{username}

MixMint gets:
  - All SEO authority (no split)
  - Google indexes mixmint.site/dj/{username} as the canonical
  - Custom domain benefits DJ's personal branding, not search rank

Why this approach:
  - Prevents duplicate content penalty on both domains
  - MixMint domain builds authority over time
  - DJs still benefit from custom domain for branding
  - Buyers searching Google find mixmint.site (good for platform)
```

---

## Implementation

```html
<!-- On custom domain (music.djrohit.com) -->
<head>
  <title>DJ Rohit — Official Store</title>

  <!-- Canonical always points to MixMint -->
  <link rel="canonical" href="https://mixmint.site/dj/rohit">

  <!-- But OG tags use the custom domain for branding -->
  <meta property="og:url" content="https://music.djrohit.com">
  <meta property="og:title" content="DJ Rohit — Buy My Music">
  <meta property="og:image" content="https://cdn.mixmint.site/avatars/rohit/medium.webp">
  <meta property="og:description" content="Official store of DJ Rohit. House, Techno, Bollywood remixes.">

  <!-- Robots: index the custom domain but canonical handles dedup -->
  <meta name="robots" content="index, follow">
</head>
```

---

## Communication to DJs

In DJ Dashboard → Store Settings → Custom Domain section:

```
ℹ️ About SEO and your custom domain

Your custom domain (music.djrohit.com) makes your store
look professional and is great for sharing on social media.

For Google search ranking: your MixMint URL
(mixmint.site/dj/rohit) is the canonical address
and benefits from MixMint's domain authority.

Sharing your custom domain link on Instagram or WhatsApp
will show beautiful preview cards with your name and photo.
```

---
---

# GAP 13 — BUYER PROFILE PAGE

## What Buyers Need

Minimal — buyers are not the public-facing side of MixMint. They need just enough to personalise their experience.

---

## Buyer Profile (Settings → My Profile)

```
┌──────────────────────────────────────────────────────────────┐
│  My Profile                                                  │
│                                                              │
│  [Avatar — circle, 80px]  [Upload Photo]                   │
│                                                              │
│  Display Name: [ Ravi Kumar          ]                      │
│  (Shown on ratings and disputes)                            │
│                                                              │
│  Email: ravi@example.com  (cannot change here — contact    │
│         support to change email)                            │
│                                                              │
│  City: [ Mumbai                      ]  (optional)         │
│  (Helps us show relevant DJ content)                        │
│                                                              │
│  [Save Profile]                                             │
└──────────────────────────────────────────────────────────────┘
```

- Avatar: stored in `mixmint-public` R2 bucket under `avatars/buyers/`
- Display name: shown on star ratings (e.g. "Ravi K. ★★★★★")
- City: used to prioritise local DJs in search/homepage
- Email change: support only (prevents account takeover)

---

## Buyer Name Display in Ratings

```
★★★★★  Ravi K.  (verified purchase)
★★★☆☆  Priya M.  (verified purchase)
```

- Last name abbreviated to initial only (privacy)
- "(verified purchase)" badge — only buyers who completed download
- No full names ever shown publicly

---

## DB Schema

```sql
ALTER TABLE profiles
  ADD COLUMN display_name VARCHAR(50),
  ADD COLUMN avatar_url VARCHAR(500),
  ADD COLUMN city VARCHAR(100),
  ADD COLUMN country VARCHAR(10) DEFAULT 'IN';
```

---
---

# GAP 14 — CHANGELOG / PLATFORM UPDATES PAGE

## URL: `/updates`

---

## Admin — Post an Update (Admin → Platform Controls → Updates)

```
┌──────────────────────────────────────────────────────────────┐
│  Post Platform Update                                        │
│                                                              │
│  Title:    [ New feature: Download Insurance now live  ]    │
│                                                              │
│  Category: [Feature ▾]  (Feature / Fix / Improvement /     │
│                           Security / DJ-only / Buyer-only)  │
│                                                              │
│  Content: [rich text or markdown]                           │
│                                                              │
│  Audience: ● Everyone  ○ DJs only  ○ Buyers only           │
│                                                              │
│  Send email digest: [✓] (batched weekly, not immediate)    │
│                                                              │
│  [Publish]  [Save Draft]                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Public Updates Page

```
┌──────────────────────────────────────────────────────────────┐
│  Platform Updates                                           │
│                                                              │
│  March 2026                                                 │
│  ──────────────────────────────────────────────────────    │
│  ✦ FEATURE   Download Insurance now available              │
│  06 Mar      Protect your purchases with one-click        │
│              insurance for just 25% of track price.        │
│                                                              │
│  ✦ FIX       Search now supports Hindi track names        │
│  04 Mar      Tracks with Hindi titles now appear in       │
│              relevant search results.                       │
│                                                              │
│  ✦ DJ        Pro plan storage increased to 20GB           │
│  01 Mar      All Pro DJ accounts upgraded automatically.  │
│                                                              │
│  February 2026                                             │
│  ──────────────────────────────────────────────────────    │
│  ...                                                        │
└──────────────────────────────────────────────────────────────┘
```

- Category badges: colour-coded pills (mint=Feature, amber=DJ, blue=Fix)
- Newest first
- Simple, clean — no comments, no reactions

---

## DB Schema

```sql
CREATE TABLE platform_updates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(200),
  content TEXT,
  category VARCHAR(20),
    -- 'feature' | 'fix' | 'improvement' | 'security' | 'dj' | 'buyer'
  audience VARCHAR(10) DEFAULT 'all',
    -- 'all' | 'dj' | 'buyer'
  published BOOLEAN DEFAULT FALSE,
  email_digest_sent BOOLEAN DEFAULT FALSE,
  created_by UUID REFERENCES profiles(id),
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---
---

# GAP 15 — CUSTOM ERROR PAGES

## 404 — Page Not Found

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  [MixMint Logo]                                             │
│                                                              │
│  404                                                        │
│  This track has left the building.                         │
│                                                              │
│  The page you're looking for doesn't exist                 │
│  or may have been removed.                                  │
│                                                              │
│  [Browse Music →]    [Go Home]                             │
│                                                              │
│  Looking for something specific?                           │
│  [Search MixMint...]                                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 500 — Server Error

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  [MixMint Logo]                                             │
│                                                              │
│  500                                                        │
│  Something went wrong on our end.                          │
│                                                              │
│  We've been notified and are looking into it.              │
│  Please try again in a few minutes.                        │
│                                                              │
│  [Try Again]    [Go Home]                                  │
│                                                              │
│  If this keeps happening: support@mixmint.site             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 403 — Forbidden

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  [MixMint Logo]                                             │
│                                                              │
│  403                                                        │
│  You don't have access to this page.                       │
│                                                              │
│  This area requires different permissions.                 │
│  If you think this is a mistake, contact support.         │
│                                                              │
│  [Go to My Dashboard]    [Go Home]                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Implementation (Django)

```python
# views/errors.py

def handler404(request, exception=None):
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    return render(request, 'errors/500.html', status=500)

def handler403(request, exception=None):
    return render(request, 'errors/403.html', status=403)

# urls.py (root)
handler404 = 'mixmint.views.errors.handler404'
handler500 = 'mixmint.views.errors.handler500'
handler403 = 'mixmint.views.errors.handler403'
```

---

## Design Rules for Error Pages

```
All error pages must:
  ✓ Include MixMint navbar (or at minimum logo)
  ✓ Respect current theme (dark/light)
  ✓ Include at least one clear action link
  ✓ NOT expose technical error details to users
  ✓ Log error details to Sentry (not shown to user)
  ✓ Have a subtle branded tone (not clinical)
  ✓ Work without JavaScript
```

---
---


# ═══════════════════════════════════════════════════
# SECTION D — IMPROVEMENT 19: DARK PATTERN AUDIT
# ═══════════════════════════════════════════════════
# IMPROVEMENT 19 — DARK PATTERN AUDIT

## Every Flow Audited

---

### ✅ PASS — Already Clean

```
Checkout shows single price           ✓ No hidden fee reveal
Trial requires no card                ✓ No forced billing
Cancel anytime messaging              ✓ Stated clearly
Content responsibility disclosure     ✓ Present everywhere relevant
```

---

### ⚠️ FIX THESE — Dark Patterns Found

---

**Pattern 1: Re-download fee not prominent at purchase**

Current state: Buyer purchases, downloads, then discovers re-download costs 50%.
Dark pattern: Material information hidden until after purchase.

Fix — Add to track detail page, ABOVE the buy button:
```
┌──────────────────────────────────────────────────────┐
│  ℹ️ Download policy                                  │
│  One secure download. Re-download available after   │
│  2 days for 50% of this price (₹25).               │
│  Download Insurance available for unlimited access. │
└──────────────────────────────────────────────────────┘
```
- Show before purchase, always
- Not in fine print — in a visible info box

---

**Pattern 2: 2-day IP lock not explained before purchase**

Current state: Buyer discovers device lock after downloading.
Fix — Same info box as above, add: *"File locked to your device for 48 hours after download."*

---

**Pattern 3: Attempt limit not shown before first download**

Current state: Buyer discovers 3-attempt limit only when they see "Attempt 1 of 3."
Fix — Show on download page before they click Download:
```
ℹ️ You have 3 download attempts for this purchase.
```
Not scary — just honest.

---

**Pattern 4: Pro trial — cancellation path must be obvious**

Current state: Trial starts, cancellation path not specified.
Fix — In trial confirmation screen AND in DJ dashboard during trial:
```
Cancel trial: Settings → Billing → Cancel Pro Trial
You will not be charged if cancelled before [exact date + time].
```
Make cancellation one tap, not buried.

---

**Pattern 5: Overage billing — is it opt-in or opt-out?**

Current state: Auto-charge on overage (they chose this — but DJ may not realise).
Fix — In Pro plan page FAQ and onboarding:
```
"Storage overage: If you exceed 20GB, additional storage is
automatically billed at ₹30/GB/month. You can disable auto-charge
in Settings → Storage, which will pause uploads instead."
```
Give DJs an opt-out. They chose auto-charge by default but can switch.

---

**Pattern 6: No price anchoring manipulation**

Check: Are we showing strikethrough prices that were never real?
Rule: Only show strikethrough prices when:
- A genuine discount is active (admin-enabled offer)
- The original price was real and charged previously

Never manufacture fake "original prices" to make discounts look bigger.

---

## Dark Pattern Audit Sign-Off Checklist

```
Before launch, confirm all are PASS:

[ ] Re-download fee shown before purchase
[ ] Device lock shown before purchase
[ ] Attempt limit shown on download page
[ ] Pro trial cancellation path clearly stated
[ ] Overage opt-out option exists and is documented
[ ] No fake strikethrough prices anywhere
[ ] Checkout total matches track page price exactly
[ ] No pre-checked upsells in checkout
[ ] No countdown timers creating false urgency
    (offer expiry dates are real admin-set dates — OK)
[ ] No misleading "limited slots" messaging
[ ] Unsubscribe from emails works in one click
```

---
---


---

# ═══════════════════════════════════════════════════
# END OF PHASE 2 — OPERATIONS & TRUST
# ═══════════════════════════════════════════════════

```
Phase 2 complete when:
  ✓ Google AdSense active — ad revenue attributed to DJs weekly
  ✓ GST invoices generating correctly for every purchase
  ✓ SEO: track pages indexed, OG tags working on WhatsApp shares
  ✓ Sitemap submitted to Google Search Console
  ✓ In-app notifications live via Supabase Realtime
  ✓ Email unsubscribe working (one-click for all categories)
  ✓ DJ directory live and searchable
  ✓ Collaboration request system functional
  ✓ Preview URL validation running daily cron
  ✓ Platform health dashboard showing real metrics
  ✓ Dark pattern audit passed — all 10 items clean
  ✓ Custom error pages live (404, 500, 403)
  ✓ Download Insurance purchasable
  ✓ Dispute resolution flow tested end-to-end

→ Proceed to Phase 3: Growth & Scale
```
