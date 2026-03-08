# 🎛️ MIXMINT — PHASE 3: GROWTH & SCALE
### *Build when Phase 2 is stable. Focus shifts from function to acquisition.*
### *Version: Final · March 2026*

---

## PHASE 3 SCOPE

```
Goal:         Grow the platform. More DJs, more buyers, more revenue.
              Surface features that increase discovery, retention,
              and average order value.

Prerequisites:
  → Phase 1 + Phase 2 fully deployed
  → Platform processing real revenue consistently
  → At least 20 active DJs
  → At least 100 buyers with purchase history
  → No HIGH or CRITICAL bugs open

Includes:
  → Track bundling (increases avg order value)
  → Buyer wishlist (increases return visits)
  → DJ announcement posts (increases storefront engagement)
  → DJ earnings forecasting (increases DJ motivation)
  → Ambassador program (controlled DJ acquisition)
  → PWA support (increases mobile return visits)
  → Track embed widget (external acquisition)
  → Hindi language support (Tier 2/3 expansion)
  → Loading states & skeleton screens (perceived performance)
  → Price formatting standard (consistency)
  → Browser tab titles (professional polish)
  → Favicon & app icons (brand polish)
  → Pre-launch master checklist (for any future sub-platforms)
```

---

## PHASE 3 BUILD ORDER

```
Step 1   Section D   Improvements 11–18 (Growth Features)
         Imp 11:     DJ Earnings Forecasting
         Imp 12:     Track Bundling
         Imp 13:     Buyer Wishlist
         Imp 14:     DJ Announcement Posts
         Imp 15:     Ambassador Program
         Imp 16:     PWA Support
         Imp 17:     Track Embed Widget
         Imp 18:     Hindi Language Support
Step 2   Section E   Polish Gaps
         Gap 16:     Loading States & Skeleton Screens
         Gap 17:     Price Formatting Standard
         Gap 18:     Browser Tab Titles
         Gap 19:     Favicon & App Icons
Step 3   Section D   Improvement 20
         Imp 20:     Pre-Launch Master Checklist
                     (adapt for any future sub-platform launches)
Step 4   Full regression test across all 3 phases
```

---


# ═══════════════════════════════════════════════════
# SECTION D — GROWTH IMPROVEMENTS 11–18
# ═══════════════════════════════════════════════════
# IMPROVEMENT 11 — DJ EARNINGS FORECASTING

## Location: DJ Dashboard → Earnings → Forecast Section

---

## Forecast Logic

```python
def calculate_earnings_forecast(dj_id):
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0)
    days_elapsed = now.day
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_remaining = days_in_month - days_elapsed

    # Earnings so far this month
    earned_this_month = Purchase.objects.filter(
        dj_id=dj_id,
        created_at__gte=month_start,
        status='active',
        download_completed=True
    ).aggregate(total=Sum('dj_revenue'))['total'] or 0

    # Daily run rate
    daily_rate = earned_this_month / days_elapsed if days_elapsed > 0 else 0

    # Projected month end
    projected_total = earned_this_month + (daily_rate * days_remaining)

    # Best month ever
    best_month = get_best_month_earnings(dj_id)

    # % of best month tracking
    if best_month > 0:
        pace_vs_best = (projected_total / best_month) * 100
    else:
        pace_vs_best = None

    # Last month comparison
    last_month_total = get_last_month_earnings(dj_id)
    if last_month_total > 0:
        vs_last_month = ((projected_total - last_month_total)
                         / last_month_total * 100)
    else:
        vs_last_month = None

    return {
        'earned_this_month': earned_this_month,
        'projected_total': projected_total,
        'daily_rate': daily_rate,
        'days_remaining': days_remaining,
        'best_month': best_month,
        'pace_vs_best': pace_vs_best,
        'vs_last_month': vs_last_month
    }
```

---

## UI Display

```
┌──────────────────────────────────────────────────────────────┐
│  EARNINGS FORECAST — March 2026                             │
│                                                              │
│  Earned so far:      ₹8,400                                │
│  Daily run rate:     ₹420/day                              │
│  Days remaining:     16                                     │
│                                                              │
│  Projected month end:  ₹15,120                             │
│                        ████████████████░░░░  52% complete  │
│                                                              │
│  vs Last month:      ↑ +23% ahead of pace                  │
│  vs Best month:      ₹18,200 · tracking 83% of your best  │
│                                                              │
│  ⚡ At this pace, you'll hit ₹15K this month.             │
│     Upload 2 more tracks to boost your chances.           │
└──────────────────────────────────────────────────────────────┘
```

- Progress bar: mint fill, shows % of month elapsed vs % of projected goal
- Forecast numbers in DM Mono
- Contextual tip at bottom — only shows if DJ has < 5 active tracks

---

## Forecast Accuracy Disclaimer

Small muted text below:
> *"Forecast based on your earnings pace so far this month. Actual results may vary."*

---
---

# IMPROVEMENT 12 — TRACK BUNDLING

## What Bundles Are
DJ-created collections of their own tracks sold as a discounted package. Not the same as albums (which are ZIP files). Bundles are multiple individually-listed tracks grouped under one purchase price.

---

## Bundle Rules

```
Minimum tracks in bundle:   2
Maximum tracks in bundle:   10
Minimum bundle price:       ₹99
Tracks must be:             DJ's own tracks, active, approved
Bundle discount range:      Admin-set (suggested 10–40% off sum)
Bundle pricing:             DJ sets the bundle price directly
Buyer gets:                 Download access to each track individually
                            (each track in their library separately)
```

---

## DJ Bundle Creation (Dashboard → My Tracks → Bundles → Create Bundle)

```
┌──────────────────────────────────────────────────────────────┐
│  Create a Bundle                                            │
│                                                              │
│  Bundle Name:     [ House Essentials Pack         ]         │
│  Description:     [ My top 5 house tracks of 2026 ]        │
│                                                              │
│  Select Tracks:                                             │
│  [✓] Track 1 — Deep Blue (₹49)                            │
│  [✓] Track 2 — Sunset Mix (₹59)                           │
│  [✓] Track 3 — Night Mode (₹49)                           │
│  [ ] Track 4 — Bass Drop (₹79)                            │
│  [ ] Track 5 — Morning (₹49)                              │
│                                                              │
│  Individual total:     ₹157                                │
│                                                              │
│  Bundle Price:         ₹[ 119 ]                            │
│                        = 24% off individual prices          │
│  Minimum: ₹99                                              │
│                                                              │
│  💡 Buyer sees: ₹119 (inclusive of all charges)           │
│     Your earnings: ₹119 × 90% = ₹107.10                  │
│                                                              │
│  [Publish Bundle]  [Save Draft]                            │
└──────────────────────────────────────────────────────────────┘
```

---

## Bundle Display (Public)

On DJ storefront — new tab: `Tracks` · `Albums` · `Bundles`

Bundle card:
```
┌──────────────────────────────────────────────────────────┐
│  [Collage of 3 track artworks]                          │
│  House Essentials Pack                                  │
│  3 tracks · Save 24%                                    │
│  ₹119  ~~₹157~~                                        │
│  [Buy Bundle]                                           │
└──────────────────────────────────────────────────────────┘
```

- Strikethrough original price in muted text
- Savings % badge top-right
- Track count shown

---

## Purchase & Download Flow

On bundle purchase:
- Single payment of bundle price
- Each track added to library individually
- Buyer can download each track separately
- Each track follows normal token/attempt rules
- One invoice for the bundle (itemised internally)

---

## DB Schema

```sql
CREATE TABLE bundles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dj_id UUID REFERENCES profiles(id),
  title VARCHAR(200),
  description TEXT,
  price INTEGER,             -- in paise
  is_active BOOLEAN DEFAULT TRUE,
  is_deleted BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bundle_tracks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_id UUID REFERENCES bundles(id),
  track_id UUID REFERENCES tracks(id),
  display_order INTEGER DEFAULT 0,
  UNIQUE(bundle_id, track_id)
);

CREATE TABLE bundle_purchases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_id UUID REFERENCES bundles(id),
  user_id UUID REFERENCES profiles(id),
  gateway_payment_id VARCHAR(255),
  amount_paid INTEGER,
  dj_revenue INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
-- On purchase: create individual Purchase records for each track
```

---
---

# IMPROVEMENT 13 — BUYER WISHLIST / SAVE FOR LATER

## Behavior

- Heart icon (♡) on every track card and track detail page
- Tap to save — fills to ♥, shows toast: *"Saved to your wishlist"*
- Tap again to remove — returns to ♡
- Saved to buyer's account (requires login)
- If not logged in: prompt auth modal → after login, track is saved

---

## Wishlist Page (Profile → My Wishlist)

```
┌──────────────────────────────────────────────────────────────┐
│  MY WISHLIST  (14 tracks)                                   │
│                                                              │
│  [Same track card grid as browse]                          │
│  Each card has ♥ filled + [Buy Now] button                 │
│                                                              │
│  Sort: [Date Saved] [Price: Low-High] [New Releases]       │
│                                                              │
│  If a wishlisted track is soft-deleted:                    │
│  Show as grayed out — "No longer available"               │
│  with [Remove] option                                      │
└──────────────────────────────────────────────────────────────┘
```

---

## Admin Wishlist Insights (Admin → Revenue Intelligence)

```
Most Wishlisted Tracks (last 30 days):

Track           DJ           Wishlists   Conversion%
──────────────────────────────────────────────────────
Mix 01          DJ Rohit     142         23%
Bass Pack       DJ Priya     98          31%
House Set       DJ Arjun     67          18%
```

- Conversion% = (purchases of track) / (times wishlisted)
- Low conversion + high wishlist = price may be too high
- Admin can use this data to suggest price adjustments to DJs

---

## DB Schema

```sql
CREATE TABLE wishlists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  content_id UUID NOT NULL,
  content_type VARCHAR(10),  -- 'track' | 'album' | 'bundle'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, content_id, content_type)
);
```

---
---

# IMPROVEMENT 14 — DJ ANNOUNCEMENT POSTS

## What Announcements Are
Short text posts (max 280 chars) a DJ can pin to their storefront. One active announcement at a time.

---

## Use Cases
- "New album dropping this Friday 🔥"
- "Store paused — back on 20th March"
- "Collab with DJ Priya now live!"
- "Holi Special — 5 new tracks this week"

---

## DJ Dashboard → Store Settings → Announcement

```
┌──────────────────────────────────────────────────────────────┐
│  Storefront Announcement                                    │
│                                                              │
│  [  ON  ●─────────  ]  Show announcement on storefront     │
│                                                              │
│  Message (max 280 chars):                                   │
│  [ New Holi Special album dropping Friday! 🎉     ]        │
│  [ 248/280 characters                             ]        │
│                                                              │
│  Show until: [DD/MM/YYYY]  or [No expiry]                  │
│                                                              │
│  [Save Announcement]                                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Storefront Display

Appears as a slim banner below the DJ header:

```
┌──────────────────────────────────────────────────────────────┐
│  📢  New Holi Special album dropping Friday! 🎉             │
└──────────────────────────────────────────────────────────────┘
```

- Background: `--bg-elevated`
- Left border: 3px `--accent-amber`
- 📢 icon + text in Satoshi 14px
- Disappears automatically on expiry date
- Admin can remove any DJ's announcement from moderation panel

---

## Admin Moderation
- Announcements flagged by buyers: admin can remove
- Admin can disable announcement feature platform-wide
- Filter for active announcements in content moderation

---

## DB Schema

```sql
ALTER TABLE profiles
  ADD COLUMN announcement_text VARCHAR(280),
  ADD COLUMN announcement_active BOOLEAN DEFAULT FALSE,
  ADD COLUMN announcement_expires_at TIMESTAMPTZ,
  ADD COLUMN announcement_updated_at TIMESTAMPTZ;
```

---
---

# IMPROVEMENT 15 — AMBASSADOR PROGRAM

## How It Works
Admin selects trusted DJs as MixMint Ambassadors. They get a unique referral link. When a new DJ signs up via that link AND gets approved within 30 days, the ambassador earns a credit.

No public signup for ambassador status. No leaderboards. No points. Admin-controlled only.

---

## Ambassador Benefits

```
Per approved DJ referred:    ₹X platform credit (admin-set, e.g. ₹500)
Credit use:                  Applied to Pro plan subscription
                             OR added to next payout
Maximum credits per month:   Admin-set (e.g. ₹2,000 cap)
```

---

## Admin Controls (Admin → Growth → Ambassadors)

```
┌──────────────────────────────────────────────────────────────┐
│  AMBASSADOR PROGRAM                                         │
│                                                              │
│  [  ON  ●─────────  ]  Program active                      │
│                                                              │
│  Per-referral credit:    ₹[ 500 ]                          │
│  Monthly credit cap:     ₹[ 2000 ]                         │
│  Attribution window:     [ 30 ] days                       │
│                                                              │
│  Active Ambassadors:                                        │
│  DJ Name       Link              Referrals  Credits Earned  │
│  ─────────────────────────────────────────────────────────  │
│  DJ Rohit      /join/rohit123    5          ₹2,500          │
│  DJ Priya      /join/priya456    2          ₹1,000          │
│                                                              │
│  [+ Add Ambassador]  [Remove]  [Export Report]             │
└──────────────────────────────────────────────────────────────┘
```

---

## Ambassador Link Tracking

```python
def track_ambassador_signup(request, ambassador_code):
    """
    Called when someone visits /join/{code}
    Sets a cookie for 30-day attribution
    """
    ambassador = DJProfile.objects.get(
        ambassador_code=ambassador_code,
        is_ambassador=True
    )
    response = redirect('/signup?role=dj')
    response.set_cookie(
        'mm_ambassador',
        ambassador.id,
        max_age=30*24*60*60,  # 30 days
        httponly=True,
        samesite='Lax'
    )
    return response


def apply_ambassador_credit_on_approval(new_dj_id):
    """Called when admin approves a new DJ application"""
    ambassador_id = get_ambassador_from_cookie_or_session(new_dj_id)
    if not ambassador_id:
        return

    credit_amount = settings.AMBASSADOR_CREDIT_PER_REFERRAL

    # Check monthly cap
    this_month_credits = AmbassadorCredit.objects.filter(
        ambassador_id=ambassador_id,
        created_at__month=timezone.now().month
    ).aggregate(total=Sum('amount'))['total'] or 0

    if this_month_credits >= settings.AMBASSADOR_MONTHLY_CAP:
        return  # Cap reached, no credit

    AmbassadorCredit.objects.create(
        ambassador_id=ambassador_id,
        referred_dj_id=new_dj_id,
        amount=credit_amount
    )

    # Add credit to ambassador's wallet
    DJWallet.objects.filter(dj_id=ambassador_id).update(
        pending_earnings=F('pending_earnings') + credit_amount
    )

    send_ambassador_credit_email(ambassador_id, credit_amount, new_dj_id)
```

---
---

# IMPROVEMENT 16 — PWA SUPPORT

## What This Adds
MixMint becomes installable on phones like a native app. "Add to Home Screen" prompt appears on Android and iOS. No app store required.

---

## Files Needed

### `manifest.json`
```json
{
  "name": "MixMint",
  "short_name": "MixMint",
  "description": "India's secure DJ music marketplace",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0A0A0F",
  "theme_color": "#00FFB3",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/static/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "screenshots": [
    {
      "src": "/static/screenshots/browse.png",
      "sizes": "390x844",
      "type": "image/png"
    }
  ]
}
```

### `service-worker.js` (minimal — cache key pages)
```javascript
const CACHE_NAME = 'mixmint-v1';
const STATIC_ASSETS = [
  '/',
  '/offline.html',
  '/static/css/main.css',
  '/static/js/main.js',
  '/static/icons/icon-192.png'
];

// Install: cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
});

// Fetch: network first for API, cache first for static
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // API calls: always network (never cache purchases/downloads)
  if (url.pathname.startsWith('/api/')) {
    return;  // Skip service worker for API
  }

  // Static assets: cache first
  event.respondWith(
    caches.match(event.request).then(cached => {
      return cached || fetch(event.request).catch(() => {
        // Offline fallback for navigation
        if (event.request.mode === 'navigate') {
          return caches.match('/offline.html');
        }
      });
    })
  );
});
```

### `offline.html` (shown when no connection)
```html
<!-- Branded offline page -->
<h1>You're offline</h1>
<p>MixMint needs a connection for browsing and downloads.</p>
<p>Your purchased tracks are in your Library when you're back online.</p>
```

---

## HTML Head Tags

```html
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#00FFB3"
      media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#007A55"
      media="(prefers-color-scheme: light)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style"
      content="black-translucent">
<meta name="apple-mobile-web-app-title" content="MixMint">
<link rel="apple-touch-icon" href="/static/icons/icon-192.png">
```

---
---

# IMPROVEMENT 17 — TRACK EMBED WIDGET

## What It Is
A small, embeddable HTML widget DJs can place on any external page — their link-in-bio, personal website, etc. Shows their top 3 tracks with prices and a "Buy on MixMint" button.

---

## Widget UI

```
┌─────────────────────────────────┐
│  🎛️ DJ Rohit on MixMint        │
│                                 │
│  [Art] Deep Blue      ₹49 [Buy]│
│  [Art] Sunset Mix     ₹59 [Buy]│
│  [Art] Night Mode     ₹49 [Buy]│
│                                 │
│  mixmint.site/dj/rohit  →      │
└─────────────────────────────────┘
```

---

## Embed Code (DJ gets this from Dashboard)

```html
<iframe
  src="https://mixmint.site/widget/dj/rohit?tracks=3&theme=dark"
  width="320"
  height="240"
  frameborder="0"
  scrolling="no"
  style="border-radius: 12px; border: none;">
</iframe>
```

---

## Widget Page (`/widget/dj/{username}`)

```python
def dj_widget(request, username):
    """
    Lightweight page served in iframe.
    No nav, no ads, no clutter.
    Just tracks + buy buttons.
    """
    dj = get_object_or_404(
        Profile,
        username=username,
        role='dj',
        store_paused=False
    )
    tracks = Track.objects.filter(
        dj_id=dj.id,
        is_active=True,
        is_deleted=False,
        file_status='ready'
    ).order_by('-created_at')[:3]

    theme = request.GET.get('theme', 'dark')

    return render(request, 'widget.html', {
        'dj': dj,
        'tracks': tracks,
        'theme': theme,
        'base_url': settings.BASE_URL
    })
```

### Parameters
```
?tracks=3        Number of tracks to show (1–5)
?theme=dark      dark | light | auto
?sort=recent     recent | popular
```

---

## Widget Dashboard Section (DJ Dashboard → Store Settings)

```
┌──────────────────────────────────────────────────────────────┐
│  Embed Widget                                               │
│                                                              │
│  Share your MixMint storefront anywhere.                   │
│                                                              │
│  Preview:  [Live preview of widget rendered here]          │
│                                                              │
│  Customise:                                                 │
│  Tracks to show: [3 ▾]   Theme: [Dark ▾]                  │
│                                                              │
│  Embed code:                                               │
│  [<iframe src="mixmint.site/widget/dj/rohit...>  [Copy]   │
│                                                              │
│  Direct link:                                               │
│  [mixmint.site/dj/rohit                        ]  [Copy]  │
└──────────────────────────────────────────────────────────────┘
```

---
---

# IMPROVEMENT 18 — HINDI LANGUAGE SUPPORT

## Scope: Partial Translation (High ROI sections only)

Full translation is expensive. Focus on the moments where Hindi reduces friction most:

```
Translate:          Don't translate yet:
──────────────────  ────────────────────────────
Navigation labels   Admin dashboard
Button CTAs         DJ analytics
Checkout flow       Legal documents (keep English)
Error messages      Email notifications (Phase 2)
Price labels        Pro plan page
Download page       Settings
Auth pages
```

---

## Implementation Approach

```python
# Django i18n
# settings.py
LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('en', 'English'),
    ('hi', 'हिंदी'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']

# In templates
{% load i18n %}
{% trans "Buy & Download" %}
{% trans "Secure one-time download. Device-locked." %}
```

---

## Language Toggle

In navbar (right side, near theme toggle):
```
EN | हिं
```

- DM Mono 12px
- Stores preference in `localStorage: mm-lang`
- Respects `Accept-Language` browser header on first visit

---

## Key Strings (Hindi Translations)

```
English                           Hindi
──────────────────────────────────────────────────────────────
"Buy & Download"                  "खरीदें और डाउनलोड करें"
"Secure one-time download"        "सुरक्षित एकबारीय डाउनलोड"
"You Pay"                         "आप देंगे"
"Inclusive of all charges"        "सभी शुल्क सहित"
"Add to Wishlist"                 "विशलिस्ट में जोड़ें"
"Login"                           "लॉग इन"
"Sign Up"                         "साइन अप"
"My Library"                      "मेरी लाइब्रेरी"
"Browse Music"                    "संगीत ब्राउज़ करें"
"Become a DJ Partner"             "DJ पार्टनर बनें"
"Download Now"                    "अभी डाउनलोड करें"
"Token expiring — download now"   "टोकन समाप्त हो रहा है — अभी डाउनलोड करें"
"Final attempt"                   "अंतिम प्रयास"
"Download complete"               "डाउनलोड पूर्ण"
"Payment confirmed"               "भुगतान की पुष्टि हुई"
```

---
---


# ═══════════════════════════════════════════════════
# SECTION E — POLISH GAPS 16–19
# ═══════════════════════════════════════════════════
# GAP 16 — LOADING STATES FOR SLOW CONNECTIONS

## Skeleton Screens (Not Spinners)

Spinners feel slow. Skeleton screens feel fast. Use skeletons for all content loads.

---

## Track Card Skeleton

```css
/* Skeleton animation */
@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.skeleton {
  animation: skeleton-pulse 1.5s ease-in-out infinite;
  background: var(--bg-elevated);
  border-radius: 8px;
}
```

```jsx
// TrackCardSkeleton.jsx
function TrackCardSkeleton() {
  return (
    <div className="track-card skeleton-card">
      <div className="skeleton artwork-skeleton" />  {/* Square artwork */}
      <div className="skeleton title-skeleton" />     {/* Title line */}
      <div className="skeleton dj-skeleton" />        {/* DJ name line */}
      <div className="skeleton price-skeleton" />     {/* Price */}
    </div>
  )
}

// Show 8 skeletons while loading
function TrackGrid({ tracks, loading }) {
  if (loading) {
    return (
      <div className="track-grid">
        {Array(8).fill(0).map((_, i) => (
          <TrackCardSkeleton key={i} />
        ))}
      </div>
    )
  }
  return <div className="track-grid">{tracks.map(t => <TrackCard track={t} />)}</div>
}
```

---

## DJ Storefront Skeleton

```jsx
function StorefrontSkeleton() {
  return (
    <div>
      {/* Banner */}
      <div className="skeleton banner-skeleton" style={{height: '200px'}} />

      {/* DJ Header */}
      <div className="dj-header">
        <div className="skeleton avatar-skeleton" />
        <div>
          <div className="skeleton name-skeleton" />
          <div className="skeleton genre-skeleton" />
        </div>
      </div>

      {/* Track grid */}
      <div className="track-grid">
        {Array(6).fill(0).map((_, i) => <TrackCardSkeleton key={i} />)}
      </div>
    </div>
  )
}
```

---

## Download Page Loading States

```
State 1 — Preparing download (0–2 seconds):
  "Preparing your secure download..."
  [Animated mint dots]

State 2 — Download started:
  "Downloading... X MB/s"
  [Progress bar animating]

State 3 — Slow connection detected (speed < 0.5 MB/s):
  ⚠️ "Slow connection detected. Your download will take longer than usual."
  "Do not close this tab."
  [Progress bar continues — doesn't freeze UI]

State 4 — Stalled (no progress for 30 seconds):
  "Download appears to have stalled."
  [Try Again — uses same attempt] [Contact Support]
```

---

## Progressive Image Loading

```javascript
// For track artwork — load small first, then swap to full
function ProgressiveImage({ smallSrc, largeSrc, alt }) {
  const [src, setSrc] = useState(smallSrc)
  const [blur, setBlur] = useState(true)

  useEffect(() => {
    const img = new Image()
    img.onload = () => {
      setSrc(largeSrc)
      setBlur(false)
    }
    img.src = largeSrc
  }, [largeSrc])

  return (
    <img
      src={src}
      alt={alt}
      style={{
        filter: blur ? 'blur(8px)' : 'none',
        transition: 'filter 0.3s ease'
      }}
    />
  )
}
```

---
---

# GAP 17 — PRICE FORMATTING STANDARD

## The Rule (Apply Everywhere, No Exceptions)

```
Format:         ₹ followed immediately by number (no space)
Thousands:      Comma separator (Indian style: ₹1,00,000)
Decimals:       Never shown for whole rupee amounts
                Only shown when paise involved (rare)
Large numbers:  ₹1,500 not ₹1500
                ₹10,000 not ₹10000

Examples:
  Track price:        ₹49
  Album price:        ₹199
  DJ earnings:        ₹12,450
  Overage charge:     ₹72
  Payout amount:      ₹3,150
  TDS deducted:       ₹350
  Pro plan monthly:   ₹299
  Pro plan annual:    ₹2,499
  Platform revenue:   ₹1,24,500  (Indian number format above lakh)
```

---

## Formatting Utility Function

```javascript
// utils/formatPrice.js

export function formatPrice(amountInPaise) {
  const rupees = Math.floor(amountInPaise / 100)
  const paise = amountInPaise % 100

  // Indian number formatting (lakhs, crores)
  const formatted = rupees.toLocaleString('en-IN')

  if (paise === 0) {
    return `₹${formatted}`
  } else {
    return `₹${formatted}.${paise.toString().padStart(2, '0')}`
  }
}

// Usage:
formatPrice(4900)    // → "₹49"
formatPrice(29900)   // → "₹299"
formatPrice(124500)  // → "₹1,245"  (amount stored as paise)

// For display text (not interactive):
export function formatPriceCompact(amountInPaise) {
  const rupees = amountInPaise / 100
  if (rupees >= 100000) return `₹${(rupees/100000).toFixed(1)}L`
  if (rupees >= 1000) return `₹${(rupees/1000).toFixed(1)}K`
  return `₹${Math.floor(rupees)}`
}
// Used in admin KPI cards: ₹1.2L, ₹45K
```

---

## Python Equivalent (For Emails and PDFs)

```python
def format_price(amount_in_paise: int) -> str:
    """Format paise to ₹ display string"""
    rupees = amount_in_paise // 100
    paise = amount_in_paise % 100

    # Indian number formatting
    s = str(rupees)
    if len(s) > 3:
        # Apply Indian grouping: last 3 digits, then groups of 2
        result = s[-3:]
        s = s[:-3]
        while s:
            result = s[-2:] + ',' + result
            s = s[:-2]
        formatted = result
    else:
        formatted = s

    if paise == 0:
        return f"₹{formatted}"
    return f"₹{formatted}.{paise:02d}"

# Tests:
# format_price(4900)     → "₹49"
# format_price(124500)   → "₹1,245"
# format_price(10000000) → "₹1,00,000"
```

---

## Where Each Format Is Used

```
Format              Used for
────────────────────────────────────────────────
₹49                 Track/album/bundle prices
₹12,450             DJ earnings, payout amounts
₹299                Pro plan pricing
₹1,24,500           Admin KPI totals
₹1.2L               Admin compact KPI cards
₹49.50              Only if paise involved (rare)
```

---
---

# GAP 18 — BROWSER TAB TITLES

## Title Formula Per Page

```
Page                    Title Format
──────────────────────────────────────────────────────────────────
Homepage                MixMint — India's DJ Music Marketplace
Track Detail            {Track Title} — {DJ Name} | MixMint
Album Detail            {Album Title} — {DJ Name} | MixMint
DJ Storefront           {DJ Display Name}'s Store | MixMint
Search Results          "{Query}" — Search | MixMint
  (no query)            Browse Music | MixMint
My Library              My Library | MixMint
Checkout                Checkout | MixMint
Download                Downloading... | MixMint
  (complete)            ✓ Download Complete | MixMint
Login                   Log In | MixMint
Sign Up                 Create Account | MixMint
DJ Dashboard            DJ Dashboard | MixMint
DJ Upload               Upload Track | MixMint
DJ Earnings             Earnings | MixMint
Admin Dashboard         Admin | MixMint
Pro Plan Page           MixMint Pro — More Storage, Less Commission
Security Page           Security Standards | MixMint
404                     Page Not Found | MixMint
500                     Something Went Wrong | MixMint
Updates Page            Platform Updates | MixMint
```

---

## Dynamic Title Updates (React/Next.js)

```jsx
// Using next/head or document.title

import Head from 'next/head'

// Track page
function TrackPage({ track }) {
  return (
    <>
      <Head>
        <title>{track.title} — {track.dj_name} | MixMint</title>
        <meta name="description" content={
          `Buy "${track.title}" by ${track.dj_name}. ` +
          `${track.genre} · ₹${track.display_price} · mixmint.site`
        } />
      </Head>
      {/* ... rest of page */}
    </>
  )
}

// Download page — dynamic title
function DownloadPage({ status }) {
  const title = status === 'complete'
    ? '✓ Download Complete | MixMint'
    : 'Downloading... | MixMint'

  useEffect(() => {
    document.title = title
  }, [status])
}
```

---
---

# GAP 19 — FAVICON AND APP ICONS

## Required Files

```
File                        Size      Purpose
──────────────────────────────────────────────────────────────
favicon.ico                 16×16     Legacy browsers, browser tab
favicon-32.png              32×32     Standard browser tab
favicon-180.png             180×180   Apple touch icon (iOS)
favicon-192.png             192×192   Android Chrome, PWA
favicon-512.png             512×512   PWA splash screen
favicon.svg                 SVG       Modern browsers (scalable)
og-default.png              1200×630  Default OG image for pages
                                      without specific artwork
```

---

## Favicon Design Spec

```
Symbol:      "M" letterform from Clash Display
Background:  #0A0A0F (dark — works on all browser chrome)
Color:       #00FFB3 (Electric Mint)
Style:       Clean, geometric — not rounded corners on the icon itself
             Let the browser/OS apply rounding (maskable icon for Android)

Dark browser: Mint M on dark background ← primary
Light browser: Dark M on cream — defined via SVG media query

SVG favicon with theme support:
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <style>
    @media (prefers-color-scheme: light) {
      .bg { fill: #F5F0E8; }
      .letter { fill: #007A55; }
    }
    @media (prefers-color-scheme: dark) {
      .bg { fill: #0A0A0F; }
      .letter { fill: #00FFB3; }
    }
  </style>
  <rect class="bg" width="32" height="32"/>
  <!-- M letterform paths here -->
</svg>
```

---

## HTML Head Implementation

```html
<head>
  <!-- Standard favicons -->
  <link rel="icon" type="image/x-icon" href="/favicon.ico">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">

  <!-- Apple -->
  <link rel="apple-touch-icon" sizes="180x180" href="/favicon-180.png">

  <!-- PWA -->
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#00FFB3"
        media="(prefers-color-scheme: dark)">
  <meta name="theme-color" content="#007A55"
        media="(prefers-color-scheme: light)">

  <!-- Default OG image (for pages without specific artwork) -->
  <meta property="og:image" content="https://cdn.mixmint.site/og-default.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
</head>
```

---

## OG Default Image Design (`og-default.png`)

```
1200×630px image:

Background: #0A0A0F with subtle mint diagonal stripe
Left side (60%): 
  MixMint wordmark (large, white)
  "India's DJ Music Marketplace"
  (Satoshi, muted)

Right side (40%):
  Floating mint "⚡" or "M" logomark

Bottom strip: mixmint.site in DM Mono

This is what appears when someone shares the homepage,
Pro page, security page, or any non-track page on WhatsApp.
```

---
---

# PLATFORM-WIDE COPY STANDARDS

## Voice and Tone Rules (Apply to All UI Copy)

```
DO:                             DON'T:
───────────────────────────     ──────────────────────────────
"Buy & Download"                "Purchase and retrieve file"
"Your track is live"            "Upload successful. Record created."
"Something went wrong"          "Error 500: Internal Server Error"
"We're looking into it"         "Please contact administrator"
"You own this track"            "Purchase record active"
"Storage running low"           "Storage quota 87% utilized"
"Check your connection"         "Network request failed (ETIMEDOUT)"
"Start your free trial"         "Initiate Pro trial period"
```

---

## Numbers to Always Show in Context

```
Bad:   "3 attempts remaining"
Good:  "Attempt 1 of 3 — download carefully"

Bad:   "Token expires in 180 seconds"
Good:  "3 minutes to start your download"

Bad:   "Storage: 2457 MB / 3072 MB"
Good:  "Storage: 2.4 GB of 3 GB used"

Bad:   "Commission: 10.00%"
Good:  "Platform keeps 10% · You keep 90%"
```

---

## Error Messages — Always Tell Users What to Do Next

```
Bad:   "Download failed"
Good:  "Download incomplete. Try again — you have 2 attempts left."

Bad:   "Payment declined"
Good:  "Payment didn't go through. Try a different card or UPI."

Bad:   "Invalid file format"
Good:  "Only MP3, WAV, and FLAC files are accepted. Please convert and re-upload."

Bad:   "Token expired"
Good:  "Your download link has expired. Go to your Library to generate a new one."
```

---

## Placeholders vs Real Copy

Never ship placeholder text in production:

```
Remove before launch:
  × "Lorem ipsum..."
  × "Track title here"
  × "DJ name"
  × "Coming soon"
  × "TODO: add copy here"
  × Any [brackets] in UI copy
  × Hardcoded "Test Track" or "DJ Test"
```

---
---

# FINAL PRE-LAUNCH SIGN-OFF (ADDITIONS TO CHECKLIST)

These are additions to the master checklist from Improvement #20:

```
Architecture:
[ ] Cloudflare Worker deployed and tested for large file downloads
[ ] Worker correctly rejects tampered tokens
[ ] ZIP album download tested with 200MB+ file — completes successfully
[ ] Background jobs all tested in production environment
[ ] Vercel Cron jobs firing on schedule (check logs after 24h)
[ ] Supabase Edge Functions deployed and responding

Security:
[ ] Supabase anon key has zero direct table access
[ ] Frontend uses Supabase for auth only
[ ] Django verifies all JWTs server-side
[ ] Worker secret is set and not guessable
[ ] No environment secrets in frontend bundle
  (run: grep -r "service_role" .next/ — should return nothing)

Content Quality:
[ ] All track artwork displays correctly in both themes
[ ] Artwork loads from cdn.mixmint.site (public bucket)
[ ] Audio files return 403 when accessed directly (private bucket)
[ ] OG images look correct when shared on WhatsApp (test manually)
[ ] Favicon shows correctly in Chrome, Firefox, Safari

Search:
[ ] pg_trgm extension enabled in Supabase
[ ] Full-text search returns relevant results for 10 test queries
[ ] Fuzzy search handles partial spellings correctly
[ ] Search with empty query shows latest tracks (not error)

Notifications:
[ ] Supabase Realtime enabled on notifications table
[ ] Test: DJ receives real-time notification on purchase
[ ] Notification bell badge count is accurate
[ ] Clicking notification navigates to correct page

Formatting:
[ ] All prices use ₹ format (no "Rs." or "INR")
[ ] No price shows decimal for whole rupee amounts
[ ] All page titles match the title formula
[ ] Favicon shows in browser tab (check all browsers)
[ ] No placeholder text anywhere in UI
```

---

*End of Part 2 — Medium Priority + Polish Gaps*

*Email Unsubscribe · Custom Domain SEO · Buyer Profile · Changelog*
*Error Pages · Loading States · Price Formatting · Tab Titles · Favicon*
*Platform Copy Standards · Final Pre-Launch Additions*

---

*COMPLETE FINAL GAPS DOCUMENT*
*Part 1: Critical Infrastructure (Gaps 01, 02, 03, 05, 06, 07, 08, 09, 10, 20)*
*Part 2: Medium Priority + Polish (Gaps 11–19 + Copy Standards)*
*Combined with all previous prompt documents = complete MixMint specification*

---


# ═══════════════════════════════════════════════════
# SECTION D — IMPROVEMENT 20: PRE-LAUNCH CHECKLIST
# ═══════════════════════════════════════════════════
# IMPROVEMENT 20 — PRE-LAUNCH MASTER CHECKLIST

## Business Readiness

```
Legal:
[ ] Terms of Service reviewed by lawyer
[ ] Privacy Policy compliant with IT Act 2000
[ ] DJ Content Agreement (upload responsibility)
[ ] Buyer Purchase Agreement (no-refund for completed downloads)
[ ] Refund Policy published
[ ] DMCA/Copyright process documented at /legal
[ ] GST status confirmed with CA

Payments:
[ ] Razorpay live keys active (not test)
[ ] Razorpay webhook URL registered + signature verification live
[ ] PhonePe application submitted (or Razorpay as permanent gateway)
[ ] Test: complete purchase end-to-end with real money (₹1 test)
[ ] Test: refund flow works with real payment
[ ] Settlement account verified in gateway dashboard
[ ] Chargeback notification email active

Security:
[ ] R2 bucket confirmed private (tested with unauthenticated request)
[ ] All Supabase RLS policies in place and tested
[ ] Admin account protected with 2FA
[ ] Strong password enforcement active
[ ] Rate limiting active on all endpoints
[ ] Temporary email blocklist loaded
[ ] Test: SQL injection on all input fields
[ ] Test: XSS on all text input fields
[ ] Test: token reuse attempt fails
[ ] Test: direct R2 URL returns 403
```

---

## Technical Readiness

```
Infrastructure:
[ ] Production environment variables set (no test keys, no DEBUG=True)
[ ] Database backups configured (daily minimum)
[ ] R2 bucket has versioning or lifecycle rules for archive
[ ] Vercel deployment is production branch only
[ ] Custom domain (mixmint.site) SSL active
[ ] Cloudflare proxy active (DDoS protection)
[ ] UptimeRobot monitoring all critical endpoints
[ ] Sentry error tracking receiving events

Email:
[ ] Resend domain verified (SPF, DKIM, DMARC set)
[ ] Test: send all 12 email types and confirm delivery
[ ] Test: emails don't go to spam (check Gmail + Outlook)
[ ] Unsubscribe link in all emails

Performance:
[ ] Lighthouse score > 80 on homepage
[ ] Images compressed and served from CDN
[ ] No console errors on any page
[ ] Mobile tested on real device (not just browser emulator)
```

---

## Content Readiness

```
[ ] At least 5 DJ accounts created with real uploads
[ ] At least 10 tracks live and purchasable before launch
[ ] All DJ storefronts have profile photos and bios
[ ] At least 2 DJ accounts are Verified
[ ] Homepage Featured DJs section has real DJs
[ ] All track preview URLs tested and working
[ ] Security Standards page (/security) content complete
[ ] Legal page (/legal) content complete
[ ] Contact email (support@mixmint.site) monitored
[ ] Admin account has strong password + 2FA
[ ] No placeholder/lorem ipsum text anywhere
[ ] No broken images anywhere
```

---

## Launch Day Sequence

```
T-7 days:
  → Send launch email to waitlist
  → Announce on social media (Instagram, Twitter)
  → Brief all onboarded DJs on launch date

T-1 day:
  → Final full test of purchase → download flow
  → Confirm all payments routing to correct account
  → Admin dashboard checked — all zeros look right
  → Backup taken of DB

Launch day:
  → Enable any launch offers in admin
  → Monitor first 10 purchases manually in real-time
  → Have Razorpay dashboard open
  → Have Supabase logs open
  → Have Sentry open
  → Response plan ready for first support ticket

T+1 day:
  → Review all error logs
  → Check any failed payments or downloads
  → Respond to any support emails
  → Post "we're live" update on social media

T+7 days:
  → Review first week metrics
  → Check chargeback rate
  → Follow up with any incomplete DJ onboardings
  → Identify first friction points from support tickets
```

---

## Emergency Contacts (Build This List Before Launch)

```
Razorpay support:    [save their emergency number]
Cloudflare support:  [save dashboard URL]
Supabase support:    [save Discord/support URL]
Vercel support:      [save support URL]
Your CA:             [save phone number]
Your lawyer:         [save phone number]
```

---

*End of Part 2 — Improvements 11–20*
*Earnings Forecasting · Track Bundling · Wishlist · DJ Announcements*
*Ambassador Program · PWA Support · Embed Widget · Hindi Support*
*Dark Pattern Audit · Pre-Launch Master Checklist*

---

*COMPLETE IMPROVEMENTS DOCUMENT*
*20 improvements across 2 files*
*Part 1: Fixes 01–10 (Critical & High Value)*
*Part 2: Fixes 11–20 (Medium Value, Growth & Polish)*

---


# ═══════════════════════════════════════════════════
# PLATFORM COPY STANDARDS
# ═══════════════════════════════════════════════════
# ═══════════════════════════════════════════════════
# SECTION F — TESTING, DEBUG & QA
# ═══════════════════════════════════════════════════

# 🧪 MIXMINT — COMPLETE TEST, DEBUG & FIX PROMPT
### *Full-stack QA: Every flow, every role, every edge case. Find it. Fix it.*

---

## 🎯 TESTING PHILOSOPHY

This is not a checklist — it is a **destructive audit**.
The goal is to break MixMint before real users do.

Test as:
1. A curious first-time visitor
2. A buyer trying to game the system
3. A DJ trying to exploit earnings
4. An admin managing a live platform
5. A bad actor trying to steal files

For every test:
- **Expected:** what should happen
- **Actual:** what actually happens
- **If broken:** root cause + exact fix

---

## 🗂️ TESTING PHASES

```
Phase 1  →  Auth & Registration
Phase 2  →  Browse & Discovery (unauthenticated)
Phase 3  →  Track & Album Pages
Phase 4  →  Checkout & Payment
Phase 5  →  Download System (core engine)
Phase 6  →  User Library
Phase 7  →  DJ Application Flow
Phase 8  →  DJ Dashboard — Full Audit
Phase 9  →  Admin Dashboard — Full Audit
Phase 10 →  Offer & Pricing System
Phase 11 →  Security & Exploit Attempts
Phase 12 →  Mobile & Responsive
Phase 13 →  Theme System (Dark/Light)
Phase 14 →  Email Notifications
Phase 15 →  Cross-browser & Performance
```

---

## PHASE 1 — AUTH & REGISTRATION

### 1.1 Email Registration

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 1.1.1 | Register with valid email + strong password | Account created, verification email sent | Email not sent / wrong template |
| 1.1.2 | Register with temporary/disposable email (mailinator, guerrilla, tempmail) | Blocked with message: "Temporary emails not accepted" | Domain blocklist not checked |
| 1.1.3 | Register with already-used email | Error: "Account already exists" | Silent fail or 500 error |
| 1.1.4 | Register with weak password (under 8 chars, no special char) | Blocked with password requirements shown | No server-side validation |
| 1.1.5 | Register with mismatched confirm password | Inline error shown immediately | Only caught on submit |
| 1.1.6 | Submit empty form | Each required field shows error | Only first field errors |
| 1.1.7 | Email verification link — click valid link | Account verified, redirected to homepage | Token expired too fast |
| 1.1.8 | Email verification link — click expired link | Error message + resend option | 500 error or blank page |
| 1.1.9 | Try to log in before verifying email | Blocked with "Please verify your email first" | User logs in unverified |
| 1.1.10 | Resend verification email — spam it (click 5x fast) | Rate limited after 2 attempts (60s cooldown) | Sends 5 emails, no limit |

---

### 1.2 Google OAuth

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 1.2.1 | Sign up with Google (new account) | Account created, role=user, redirected to homepage | Role not set in profiles table |
| 1.2.2 | Sign in with Google (existing account) | Logs in, session established | Duplicate profile row created |

---

# ═══════════════════════════════════════════════════
# END OF PHASE 3 — GROWTH & SCALE
# ═══════════════════════════════════════════════════

```
Phase 3 complete when:
  ✓ Track bundles live — DJs can create and sell packs
  ✓ Buyer wishlist functional with admin conversion analytics
  ✓ DJ announcements showing on storefronts
  ✓ Earnings forecasting showing in DJ dashboard
  ✓ PWA installable on Android and iOS
  ✓ Embed widget working on external sites
  ✓ Hindi translation live on checkout, nav, and key flows
  ✓ Ambassador program active for selected DJs
  ✓ All skeleton loading screens in place
  ✓ Price formatting consistent across entire platform
  ✓ All browser tab titles matching formula
  ✓ Favicon showing correctly in all browsers
  ✓ Full regression test across all 3 phases passing

  MixMint is now a complete, scalable marketplace.
```

---

*MixMint Phase 3 — Growth & Scale · March 2026*
*mixmint.site*
