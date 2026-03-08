# 🎛️ MIXMINT — THREE NEW FEATURES PROMPT
### *Feature 01: Underperforming Track Offload System*
### *Feature 02: DJ-to-DJ Track Purchase*
### *Feature 03: Cart + Bulk Download + Discount Offers*
### *Version: Final · March 2026*

---

# ═══════════════════════════════════════════════════
# FEATURE 01 — UNDERPERFORMING TRACK OFFLOAD SYSTEM
# ═══════════════════════════════════════════════════

## What It Is

When a DJ's track or album has zero or very low sales over a defined
period, MixMint notifies the DJ that the content is underperforming.
The DJ is given the option to:

1. Download the file from MixMint (one last export)
2. Upload it to Google Drive or MediaFire (external hosting)
3. Paste the external link into MixMint
4. The download button on that track is replaced with a redirect
   to the external link — file served free, no token system
5. The file is deleted from R2 (storage reclaimed)
6. Track stays live as a free external-link track — visible, browsable,
   searchable, but costs MixMint zero storage

---

## Why This Is Smart

```
For the platform:
  → Reclaims R2 storage from dead inventory
  → Reduces storage cost on zero-revenue tracks
  → Admin can push underperforming DJs to clean up

For the DJ:
  → Underperforming track gets a second life as free promo content
  → Free tracks drive DJ discovery — buyers who download for free
    may buy their paid tracks
  → DJ keeps their storefront active with more content
  → External links (GDrive/MediaFire) cost DJ nothing extra

For buyers:
  → Free content = more reason to visit MixMint
  → Discover DJs they wouldn't pay for upfront
```

---

## Underperforming Definition (Admin-Configurable)

```
Admin → Platform Controls → Underperforming Thresholds

Days since upload with zero sales:   [ 60 ]  days
OR sales below minimum in period:    [ 2  ]  sales in [ 90 ] days

Exclude from check:
  [✓] Tracks uploaded in last 30 days (too new to judge)
  [✓] Tracks already marked as external link (already offloaded)
  [✓] Tracks on paused stores
  [✓] Free tracks (already free)
```

---

## Detection Cron (Weekly — Every Monday)

```python
# /api/cron/detect-underperforming-tracks (Vercel Cron, weekly)

def detect_underperforming_tracks():
    """
    Identifies tracks/albums meeting underperform criteria.
    Sends notification to DJ. Does NOT auto-delete anything.
    All action is DJ-initiated.
    """
    thresholds = get_admin_thresholds()
    min_age_days = 30
    zero_sales_days = thresholds['zero_sales_days']        # e.g. 60
    low_sales_count = thresholds['low_sales_count']        # e.g. 2
    low_sales_period = thresholds['low_sales_period_days'] # e.g. 90
    cutoff_zero = timezone.now() - timedelta(days=zero_sales_days)
    cutoff_low  = timezone.now() - timedelta(days=low_sales_period)
    too_new     = timezone.now() - timedelta(days=min_age_days)

    tracks = Track.objects.filter(
        is_active=True,
        is_deleted=False,
        is_external_link=False,   # not already offloaded
        file_status='ready',
        created_at__lt=too_new,   # older than 30 days
        store_paused=False,
        price__gt=0               # paid tracks only
    ).annotate(
        sales_in_period=Count(
            'purchases',
            filter=Q(
                purchases__created_at__gte=cutoff_low,
                purchases__download_completed=True,
                purchases__status='active'
            )
        ),
        last_sale_at=Max(
            'purchases__created_at',
            filter=Q(purchases__status='active')
        )
    ).filter(
        Q(sales_in_period=0) |  # zero sales in period
        Q(sales_in_period__lt=low_sales_count)  # below threshold
    )

    notified_djs = set()

    for track in tracks:
        # Already notified recently? (avoid repeat spam)
        already_notified = UnderperformNotification.objects.filter(
            content_id=track.id,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).exists()
        if already_notified:
            continue

        UnderperformNotification.objects.create(
            dj_id=track.dj_id,
            content_id=track.id,
            content_type='track',
            sales_in_period=track.sales_in_period,
            period_days=low_sales_period
        )

        if track.dj_id not in notified_djs:
            notified_djs.add(track.dj_id)

    # Send one batched email per DJ (not one per track)
    for dj_id in notified_djs:
        send_underperform_digest_email(dj_id)


def send_underperform_digest_email(dj_id):
    pending = UnderperformNotification.objects.filter(
        dj_id=dj_id,
        status='pending',
        email_sent=False
    ).select_related('content')

    tracks_list = "\n".join([
        f"  · {n.content.title} ({n.sales_in_period} sales in "
        f"{n.period_days} days)"
        for n in pending
    ])

    send_email(
        to=get_dj_email(dj_id),
        subject="Some of your tracks aren't getting traction — here's what you can do",
        body=f"""
Hi {get_dj_name(dj_id)},

These tracks haven't been getting much attention:

{tracks_list}

You have two options for each:

1. Keep them as-is (no action needed)
2. Convert to a free external download — upload to Google Drive
   or MediaFire, paste the link on MixMint, and we'll serve it
   for free. This frees up your storage and may help new fans
   discover you.

Manage your tracks: https://mixmint.site/dj-panel/tracks

— MixMint Team
        """
    )
    pending.update(email_sent=True)
```

---

## DJ Dashboard — Underperforming Tracks Section

### Location: DJ Dashboard → My Tracks → tab: `Underperforming`

```
┌──────────────────────────────────────────────────────────────┐
│  UNDERPERFORMING TRACKS                                     │
│                                                              │
│  These tracks have had low or no sales in the past 90 days. │
│  Consider converting them to free external downloads to     │
│  save storage and attract new listeners.                    │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  🎵 Deep Blue (Extended Mix)                           │ │
│  │  Uploaded: 4 months ago · Sales: 0 in 90 days        │ │
│  │  Storage used: 18.4 MB                                │ │
│  │                                                        │ │
│  │  [Keep as Paid]  [Convert to Free External Link →]    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  📦 House Pack Vol.1 (Album)                           │ │
│  │  Uploaded: 6 months ago · Sales: 1 in 90 days        │ │
│  │  Storage used: 142 MB                                 │ │
│  │                                                        │ │
│  │  [Keep as Paid]  [Convert to Free External Link →]    │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Conversion Flow (Step-by-Step Modal)

When DJ clicks **[Convert to Free External Link →]**:

```
┌──────────────────────────────────────────────────────────────┐
│  Convert "Deep Blue" to Free External Download              │
│                                                              │
│  STEP 1 OF 3 — Download your file from MixMint             │
│                                                              │
│  Download your original file first so you can upload it    │
│  to Google Drive or MediaFire.                             │
│                                                              │
│  [⬇ Download My File]                                      │
│  (This uses your DJ account — no token charges)            │
│                                                              │
│  [Next →]  (enabled after download or if you already       │
│             have the file saved locally)                   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  STEP 2 OF 3 — Upload to Google Drive or MediaFire         │
│                                                              │
│  Upload your file to one of these services and get a       │
│  public shareable direct download link:                    │
│                                                              │
│  [Open Google Drive ↗]   [Open MediaFire ↗]               │
│                                                              │
│  Tips:                                                      │
│  · Google Drive: Right-click → Share → Anyone with link   │
│    → Copy link                                             │
│  · MediaFire: Upload → click file → Copy Direct Link      │
│                                                              │
│  Important: The link must be a direct download link,       │
│  not a preview or folder link.                             │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  STEP 3 OF 3 — Paste your external link                    │
│                                                              │
│  Google Drive or MediaFire link:                           │
│  [https://drive.google.com/...              ]              │
│                                                              │
│  [Verify Link]  ← checks URL is reachable (HEAD request)  │
│                                                              │
│  ✓ Link verified — file is accessible                      │
│                                                              │
│  What happens next:                                         │
│  · Track becomes FREE — no purchase required               │
│  · Download button redirects to your external link         │
│  · Your file is removed from MixMint storage              │
│  · Track stays live and searchable on MixMint             │
│  · Buyers who previously purchased still see it in        │
│    their library (their link redirects to external too)   │
│                                                              │
│  [Confirm & Convert]                                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Link Validation (Backend)

```python
import requests

def validate_external_link(url):
    """
    Validates that:
    1. URL is from allowed providers (GDrive or MediaFire)
    2. URL is reachable (not 404)
    3. URL appears to be a direct/shareable link
    """
    ALLOWED_DOMAINS = [
        'drive.google.com',
        'docs.google.com',
        'mediafire.com',
        'www.mediafire.com'
    ]

    from urllib.parse import urlparse
    parsed = urlparse(url)

    if parsed.netloc not in ALLOWED_DOMAINS:
        return False, (
            "Only Google Drive and MediaFire links are accepted. "
            f"Got: {parsed.netloc}"
        )

    # HEAD request to check reachability
    try:
        resp = requests.head(url, timeout=8, allow_redirects=True)
        if resp.status_code == 200:
            return True, None
        elif resp.status_code == 403:
            return False, (
                "Link is not publicly accessible. "
                "Make sure sharing is set to 'Anyone with the link'."
            )
        elif resp.status_code == 404:
            return False, "Link not found. Please check the URL."
        else:
            return False, f"Link returned status {resp.status_code}."
    except requests.RequestException:
        return False, "Could not reach the link. Please check and try again."
```

---

## Conversion Backend (Django View)

```python
@require_authenticated_dj
def convert_to_external_link(request, content_id, content_type):
    external_url = request.POST.get('external_url', '').strip()

    # Validate URL
    valid, error = validate_external_link(external_url)
    if not valid:
        return JsonResponse({'error': error}, status=400)

    with transaction.atomic():
        if content_type == 'track':
            content = Track.objects.get(id=content_id, dj_id=request.user_id)
            r2_key = content.file_path
            content.is_external_link = True
            content.external_link_url = external_url
            content.external_link_provider = detect_provider(external_url)
            content.price = 0           # Set to free
            content.file_path = None    # Remove R2 reference
            content.converted_at = timezone.now()
            content.save()

        elif content_type == 'album':
            content = Album.objects.get(id=content_id, dj_id=request.user_id)
            r2_key = content.file_path
            content.is_external_link = True
            content.external_link_url = external_url
            content.external_link_provider = detect_provider(external_url)
            content.price = 0
            content.file_path = None
            content.converted_at = timezone.now()
            content.save()

        # Schedule R2 deletion (24h delay — safety buffer)
        schedule_r2_deletion(r2_key, delay_hours=24)

        # Update DJ storage count
        update_dj_storage_used(request.user_id)

        # Update existing purchasers — their library now shows external link
        Purchase.objects.filter(
            content_id=content_id,
            content_type=content_type,
            status='active'
        ).update(
            download_method='external_link',
            external_link_url=external_url
        )

    return JsonResponse({
        'status': 'converted',
        'message': 'Track is now a free external download.'
    })


def detect_provider(url):
    if 'drive.google.com' in url or 'docs.google.com' in url:
        return 'google_drive'
    elif 'mediafire.com' in url:
        return 'mediafire'
    return 'other'
```

---

## Public Track Page — External Link State

When `is_external_link = True` and `price = 0`:

```
┌──────────────────────────────────────────────────────────────┐
│  [Track Artwork]                                            │
│                                                              │
│  Deep Blue (Extended Mix)                                   │
│  DJ Rohit  ·  House  ·  6:42                               │
│                                                              │
│  FREE                                                        │
│                                                              │
│  [⬇  Free Download  ↗]   ← opens external link in new tab │
│                                                              │
│  Hosted on Google Drive                                     │
│                                                              │
│  [YouTube preview embed]                                   │
└──────────────────────────────────────────────────────────────┘
```

- No login required to access the link (it's external)
- No token system (not a MixMint-hosted file)
- No attempt counting (not our server)
- "Hosted on Google Drive / MediaFire" provider badge shown
- Free badge replaces price

---

## Existing Buyers — Library Update

Buyers who previously purchased the track before it was converted:

```
┌──────────────────────────────────────────────────────────────┐
│  Library — Deep Blue (Extended Mix)                         │
│                                                              │
│  ℹ️ This track is now available as a free download.        │
│  [⬇  Download Free  ↗]  (Google Drive)                    │
└──────────────────────────────────────────────────────────────┘
```

No refund needed — content is still accessible. If buyer paid for it before conversion, no financial action is taken (they got what they paid for, it's now also free publicly).

---

## Link Health Monitoring (Weekly Cron)

```python
def check_external_link_health():
    """
    Weekly cron — checks all external links are still alive.
    Notifies DJ if their link is broken.
    """
    externals = Track.objects.filter(
        is_external_link=True,
        is_active=True,
        is_deleted=False
    )
    broken = []
    for track in externals:
        valid, error = validate_external_link(track.external_link_url)
        if not valid:
            broken.append(track)
            track.external_link_broken = True
            track.external_link_error = error
            track.save()
            send_broken_external_link_email(track.dj_id, track, error)

    if broken:
        send_admin_broken_links_report(broken)
```

### Broken Link State on Track Page

```
⚠️  Download temporarily unavailable.
    The DJ has been notified.
```

### Broken Link State in DJ Dashboard

```
⚠️  External link broken — [Update Link]
```

---

## Admin Controls (Admin → Content → Underperforming)

```
┌──────────────────────────────────────────────────────────────┐
│  UNDERPERFORMING TRACK SYSTEM                               │
│                                                              │
│  Detection thresholds:                                      │
│  Zero sales after:       [ 60 ] days                       │
│  Low sales threshold:    [ 2  ] sales in [ 90 ] days       │
│  Min track age:          [ 30 ] days (exclude newer)       │
│                                                              │
│  [  ON  ●─────  ]  Auto-notify DJs weekly                  │
│                                                              │
│  Current underperforming:                                   │
│  Tracks: 12  ·  Albums: 3  ·  Storage wasteable: 1.4 GB   │
│                                                              │
│  Converted to external:                                     │
│  Tracks: 8   ·  Albums: 1  ·  Storage reclaimed: 890 MB   │
│                                                              │
│  External links health:                                     │
│  Active: 9  ·  Broken: 0  ·  Last checked: 2 days ago     │
│                                                              │
│  [Run Detection Now]  [Export Underperforming List]        │
└──────────────────────────────────────────────────────────────┘
```

---

## DB Schema

```sql
ALTER TABLE tracks
  ADD COLUMN is_external_link BOOLEAN DEFAULT FALSE,
  ADD COLUMN external_link_url VARCHAR(1000),
  ADD COLUMN external_link_provider VARCHAR(20),
    -- 'google_drive' | 'mediafire' | 'other'
  ADD COLUMN external_link_broken BOOLEAN DEFAULT FALSE,
  ADD COLUMN external_link_error VARCHAR(200),
  ADD COLUMN converted_at TIMESTAMPTZ;

ALTER TABLE albums
  ADD COLUMN is_external_link BOOLEAN DEFAULT FALSE,
  ADD COLUMN external_link_url VARCHAR(1000),
  ADD COLUMN external_link_provider VARCHAR(20),
  ADD COLUMN external_link_broken BOOLEAN DEFAULT FALSE,
  ADD COLUMN external_link_error VARCHAR(200),
  ADD COLUMN converted_at TIMESTAMPTZ;

ALTER TABLE purchases
  ADD COLUMN download_method VARCHAR(20) DEFAULT 'mixmint',
    -- 'mixmint' | 'external_link'
  ADD COLUMN external_link_url VARCHAR(1000);

CREATE TABLE underperform_notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dj_id UUID REFERENCES profiles(id),
  content_id UUID NOT NULL,
  content_type VARCHAR(10),    -- 'track' | 'album'
  sales_in_period INTEGER,
  period_days INTEGER,
  status VARCHAR(20) DEFAULT 'pending',
    -- 'pending' | 'converted' | 'kept' | 'dismissed'
  email_sent BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---
---

# ═══════════════════════════════════════════════════
# FEATURE 02 — DJ-TO-DJ TRACK PURCHASE
# ═══════════════════════════════════════════════════

## What It Is
A DJ can purchase another DJ's tracks just like a regular buyer. They use their MixMint account (which has both a DJ role and buyer capabilities). The purchase appears in their library with the same download rules as any buyer.

Key design decisions:
- DJs pay full price — no DJ discount (prevents abuse)
- DJ's purchase is logged separately from their DJ earnings dashboard
- Purchased track goes to their personal library, not their DJ panel
- DJ cannot re-upload, re-sell, or claim any rights to purchased track
- Revenue goes to the selling DJ normally (85% after commission)

---

## Implementation — DJ Role Check

```python
def create_payment_order(request, content_id, content_type):
    user_id = request.user_id
    user_role = request.user_role  # 'user' | 'dj' | 'admin'

    # DJs can purchase just like buyers — no restriction
    # But cannot purchase their own content
    content = get_content(content_id, content_type)

    if content.dj_id == user_id:
        return JsonResponse({
            'error': 'own_content',
            'message': "You can't purchase your own track."
        }, status=400)

    # Check for existing purchase (same as buyer flow)
    existing = Purchase.objects.filter(
        user_id=user_id,
        content_id=content_id,
        status='active'
    ).first()

    if existing:
        return JsonResponse({
            'error': 'already_owned',
            'message': 'You already own this track. Find it in your Library.'
        }, status=409)

    # Proceed with normal payment flow — DJ pays full price
    # Revenue split: 15% platform, 85% to selling DJ
    # No change to revenue calculation
    proceed_with_payment(user_id, content_id, content_type)
```

---

## DJ Library (Separate from DJ Panel)

When a DJ purchases another DJ's track, it appears in:
- `/library` (the buyer library) — not `/dj-panel`
- Listed under "Purchased Tracks" in their library

```
┌──────────────────────────────────────────────────────────────┐
│  MY LIBRARY                                                  │
│                                                              │
│  [Purchased Tracks tab] [Uploaded Tracks tab (DJ only)]    │
│                                                              │
│  Purchased Tracks:                                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  🎵 Night Mode — DJ Priya                           │  │
│  │  Purchased 2 days ago · ₹59                        │  │
│  │  [⬇ Download]                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Uploaded Tracks (your DJ panel):                          │
│  [Go to DJ Panel →]                                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Navbar for DJ Users

DJ users see both modes in the nav:

```
[Browse]  [My Library]  [DJ Panel ▾]  [Account]
```

`My Library` = their purchases as a buyer
`DJ Panel` = their uploads, earnings, storefront

---

## Preventing Circular Abuse

```python
# DJs cannot:
# 1. Purchase their own tracks (blocked above)
# 2. Re-upload purchased tracks (admin moderation catches duplicates)
# 3. Claim copyright on purchased tracks (DJ agreement at upload)
# 4. Get any earnings credit for purchasing their collab partner's track

# Metadata injection on purchase does NOT tag the purchasing DJ.
# It only tags the original uploading DJ.
```

---

## Revenue Attribution for DJ Purchase

```python
def on_dj_purchases_track(purchase):
    """
    DJ buys another DJ's track.
    Revenue goes entirely to selling DJ (normal flow).
    No special handling needed — same as buyer purchase.
    """
    # Selling DJ gets 85% of purchase price
    selling_dj_revenue = purchase.original_price * Decimal('0.85')

    DJWallet.objects.filter(dj_id=purchase.dj_id).update(
        pending_earnings=F('pending_earnings') + selling_dj_revenue,
        total_earnings=F('total_earnings') + selling_dj_revenue
    )

    # Buying DJ's wallet: UNTOUCHED — they spent money, didn't earn
    # No ad revenue impact — purchase itself generates no impressions

    # Notify selling DJ: "DJ Priya purchased your track 'Night Mode'"
    create_notification(
        user_id=purchase.dj_id,  # selling DJ
        notif_type='dj_purchased_your_track',
        title='A DJ bought your track',
        body=f"DJ {purchase.buyer_name} purchased \"{purchase.track_title}\"",
        priority='normal'
    )
```

---

## DJ Earnings Dashboard — Buyer Type Visibility

In selling DJ's earnings breakdown:

```
Recent Sales — March 2026

  Date        Buyer           Track           Amount
  ──────────────────────────────────────────────────
  06 Mar      Ravi K.         Deep Blue        ₹41.65  (buyer)
  05 Mar      DJ Priya  ✦     Night Mode       ₹50.15  (DJ)  ← badge
  04 Mar      Kiran M.        Deep Blue        ₹41.65  (buyer)
```

`✦` badge indicates the buyer was a DJ — useful data for DJs to know other DJs are listening to their work.

---

## Terms and Clarity

Add to track detail page (visible to all logged-in DJs):

```
ℹ️ DJs can purchase tracks as personal inspiration or reference.
Purchased tracks are for personal use only and may not be
re-uploaded, re-sold, or used in commercial productions.
```

---

## DB Schema

```sql
-- No new tables needed. Existing purchases table handles this.
-- Add buyer_role column for analytics:

ALTER TABLE purchases
  ADD COLUMN buyer_role VARCHAR(10) DEFAULT 'user';
    -- 'user' | 'dj' | 'admin'

-- Set on purchase creation:
-- purchase.buyer_role = request.user_role
```

---
---

# ═══════════════════════════════════════════════════
# FEATURE 03 — CART + BULK DOWNLOAD + DISCOUNT OFFERS
# ═══════════════════════════════════════════════════

## What It Is

Three tightly linked features:

1. **Cart** — buyer adds multiple tracks/albums to a cart before purchasing
2. **Bulk Download** — after cart checkout, all tracks downloadable in one flow
3. **Discount Offers** — automatic price reduction for cart purchases (admin-configurable tiers)

---

## Cart Rules

```
Cart can hold:        Tracks, albums, bundles (mixed)
Cart persists:        Until purchase or manual clear (stored in DB for
                      logged-in users, localStorage for guests — converted
                      on login)
One cart per user:    Always. No named carts.
Max cart items:       20 (admin-configurable)
Can't add to cart:    Your own tracks, tracks you already own,
                      free external-link tracks (just download directly)
Cart expiry:          30 days of inactivity (items removed, user notified)
```

---

## Cart UI — Add to Cart Button

On every track card and track detail page:

```
[⊕ Add to Cart]    [Buy Now]
```

- `[⊕ Add to Cart]` — adds to cart, shows cart badge in nav
- `[Buy Now]` — existing single-track checkout (unchanged)
- If already in cart: button changes to `[✓ In Cart]` (greyed out, not clickable)
- If already owned: `[✓ Owned]`

---

## Cart Badge in Navbar

```
[Browse]  [My Library]  🛒 3  [Account]
```

Cart icon with item count badge. Clicking opens cart panel.

---

## Cart Panel (Slide-in from right, or `/cart` page)

```
┌──────────────────────────────────────────────────────────────┐
│  YOUR CART  (3 items)                              [×]      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  [Art]  Deep Blue — DJ Rohit              ₹49  [✕]  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  [Art]  Night Mode — DJ Priya             ₹59  [✕]  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  [Art]  House Pack Vol.1 — DJ Arjun      ₹199  [✕]  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Subtotal:          ₹307                                    │
│  Cart discount:    −₹31  (10% off — 3+ items)  ✦          │
│  ─────────────────────────────────────                     │
│  Total:             ₹276                                    │
│                                                              │
│  [Proceed to Checkout →]                                    │
│  [Continue Shopping]                                        │
│                                                              │
│  ✦ Buy 5+ items for 15% off                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Discount Tiers (Admin-Configurable)

```
Admin → Offers & Pricing → Cart Discounts

[  ON  ●─────  ]  Cart discount system active

Tier 1:  [ 3 ]+ items  →  [ 10 ]% off cart total
Tier 2:  [ 5 ]+ items  →  [ 15 ]% off cart total
Tier 3:  [10 ]+ items  →  [ 20 ]% off cart total

Discount applies to:   ● All items in cart
                       ○ Cheapest items only (up to tier count)

Max discount cap:      ₹[ 500 ] (no single cart saves more than this)

Show teaser to buyer:  [✓] Show "Buy X more for Y% off" nudge
                           in cart when near next tier

[Save Discount Settings]
```

---

## Discount Calculation (Backend)

```python
CART_DISCOUNT_TIERS = [
    {'min_items': 10, 'discount_pct': Decimal('0.20')},
    {'min_items': 5,  'discount_pct': Decimal('0.15')},
    {'min_items': 3,  'discount_pct': Decimal('0.10')},
]
MAX_DISCOUNT_PAISE = 50000  # ₹500

def calculate_cart_total(cart_items):
    """
    Returns subtotal, discount amount, final total, tier applied.
    """
    subtotal = sum(item['price'] for item in cart_items)
    item_count = len(cart_items)

    # Find applicable tier (highest qualifying)
    applied_tier = None
    for tier in CART_DISCOUNT_TIERS:  # already sorted high-to-low
        if item_count >= tier['min_items']:
            applied_tier = tier
            break

    if not applied_tier:
        return {
            'subtotal': subtotal,
            'discount': 0,
            'discount_pct': 0,
            'total': subtotal,
            'tier': None
        }

    raw_discount = int(subtotal * applied_tier['discount_pct'])
    discount = min(raw_discount, MAX_DISCOUNT_PAISE)

    # Teaser: how many items needed to reach next tier
    next_tier = None
    for tier in reversed(CART_DISCOUNT_TIERS):
        if tier['min_items'] > item_count:
            next_tier = {
                'items_needed': tier['min_items'] - item_count,
                'discount_pct': int(tier['discount_pct'] * 100)
            }
            break

    return {
        'subtotal': subtotal,
        'discount': discount,
        'discount_pct': int(applied_tier['discount_pct'] * 100),
        'total': subtotal - discount,
        'tier': applied_tier,
        'next_tier_teaser': next_tier  # e.g. "Add 2 more for 15% off"
    }
```

---

## Cart Discount Distribution to DJs

When a discounted cart purchase is made, the discount is distributed proportionally across all items — each DJ's revenue is reduced by their item's share of the discount:

```python
def process_cart_purchase(cart_id, payment_verified):
    cart = Cart.objects.get(id=cart_id)
    totals = calculate_cart_total(cart.items)
    discount_total = totals['discount']
    subtotal = totals['subtotal']

    purchases = []
    for item in cart.items:
        # Each item's proportional share of the discount
        item_discount = int(discount_total * (item['price'] / subtotal))
        item_final_price = item['price'] - item_discount

        # Platform commission on discounted price
        commission = int(item_final_price * Decimal('0.15'))
        dj_revenue = item_final_price - commission

        purchase = Purchase.objects.create(
            user_id=cart.user_id,
            content_id=item['content_id'],
            content_type=item['content_type'],
            dj_id=item['dj_id'],
            original_price=item['price'],
            discount_applied=item_discount,
            final_price=item_final_price,
            commission=commission,
            dj_revenue=dj_revenue,
            cart_id=cart_id,
            status='active'
        )
        purchases.append(purchase)

        # Credit DJ wallet
        DJWallet.objects.filter(dj_id=item['dj_id']).update(
            pending_earnings=F('pending_earnings') + dj_revenue,
            total_earnings=F('total_earnings') + dj_revenue
        )

    # Mark cart as purchased
    cart.status = 'purchased'
    cart.purchased_at = timezone.now()
    cart.save()

    return purchases
```

---

## Checkout — Cart Checkout Flow

```
Step 1 — Review cart (shown above)
Step 2 — Payment

┌──────────────────────────────────────────────────────────────┐
│  Checkout — 3 tracks                                        │
│                                                              │
│  Deep Blue                          ₹49                     │
│  Night Mode                         ₹59                     │
│  House Pack Vol.1                  ₹199                     │
│  ─────────────────────────────────────                     │
│  Subtotal                          ₹307                     │
│  Cart discount (10%)               −₹31                     │
│  ─────────────────────────────────────                     │
│  Total                             ₹276                     │
│                                                              │
│  [Pay ₹276 →]  (PhonePe)                                   │
└──────────────────────────────────────────────────────────────┘

Step 3 — Payment confirmed → redirect to Bulk Download page
```

---

## Bulk Download Page (`/cart/download/{cart_id}`)

After cart checkout succeeds, buyer lands on a bulk download page:

```
┌──────────────────────────────────────────────────────────────┐
│  ✓ Payment confirmed — 3 tracks ready to download          │
│                                                              │
│  Download each track:                                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  🎵 Deep Blue — DJ Rohit                            │  │
│  │  MP3 · 320 kbps · 6:42                             │  │
│  │  [⬇ Download]    ○ Not started                     │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  🎵 Night Mode — DJ Priya                           │  │
│  │  MP3 · 320 kbps · 5:18                             │  │
│  │  [⬇ Download]    ○ Not started                     │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  📦 House Pack Vol.1 — DJ Arjun                     │  │
│  │  ZIP · 6 tracks · 142 MB                           │  │
│  │  [⬇ Download]    ○ Not started                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ℹ️ Each track has its own download link and attempt count. │
│  Downloads are available in your Library anytime.          │
│                                                              │
│  [Go to My Library →]                                      │
└──────────────────────────────────────────────────────────────┘
```

### Download Status States (per item)

```
○ Not started
⟳ Downloading... (progress bar)
✓ Complete
✗ Failed — [Retry]
```

---

## Important: No "Download All as ZIP" Option

Each track is downloaded individually via the existing token system. There is no "Download All" button because:
- Each file has its own token (security model)
- ZIP bundling server-side is expensive and defeats watermarking
- Buyer can come back to Library anytime for remaining downloads

This is clearly communicated in the UI.

---

## Cart Persistence

```python
class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = models.UUIDField()
    status = models.CharField(max_length=20, default='active')
        # 'active' | 'purchased' | 'expired' | 'abandoned'
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    purchased_at = models.DateTimeField(null=True)
    expires_at = models.DateTimeField()  # 30 days from last update

class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    cart = models.ForeignKey(Cart, related_name='items',
                             on_delete=models.CASCADE)
    content_id = models.UUIDField()
    content_type = models.CharField(max_length=10)  # 'track'|'album'|'bundle'
    dj_id = models.UUIDField()
    price = models.IntegerField()  # price at time of adding to cart
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'content_id', 'content_type')
```

---

## Guest Cart → Login Conversion

```javascript
// On guest (not logged in) adding to cart:
// Store in localStorage under 'mm_guest_cart'

// On login:
async function mergeGuestCart() {
  const guestItems = JSON.parse(
    localStorage.getItem('mm_guest_cart') || '[]'
  );
  if (guestItems.length === 0) return;

  // Send to backend to merge with user's DB cart
  await fetch('/api/cart/merge/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getToken()}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ items: guestItems })
  });

  localStorage.removeItem('mm_guest_cart');
}
```

---

## Cart API Endpoints

```python
# urls.py
urlpatterns = [
    path('api/cart/',              cart_get,          name='cart_get'),
    path('api/cart/add/',          cart_add,          name='cart_add'),
    path('api/cart/remove/',       cart_remove,       name='cart_remove'),
    path('api/cart/clear/',        cart_clear,        name='cart_clear'),
    path('api/cart/merge/',        cart_merge_guest,  name='cart_merge'),
    path('api/cart/checkout/',     cart_checkout,     name='cart_checkout'),
    path('api/cart/totals/',       cart_totals,       name='cart_totals'),
    # Returns: subtotal, discount, total, tier, next_tier_teaser
]
```

---

## Abandoned Cart Recovery (7 Days)

```python
# Cron: daily — check for abandoned carts with items

def send_abandoned_cart_reminders():
    """
    Cart abandoned = active cart, no checkout, last update > 3 days ago.
    Send one reminder email per user. Never spam.
    """
    cutoff = timezone.now() - timedelta(days=3)
    abandoned_carts = Cart.objects.filter(
        status='active',
        updated_at__lt=cutoff,
        reminder_sent=False
    ).prefetch_related('items')

    for cart in abandoned_carts:
        if not cart.items.exists():
            continue

        item_count = cart.items.count()
        totals = calculate_cart_total(list(
            cart.items.values('price', 'content_id', 'content_type', 'dj_id')
        ))

        send_email(
            to=get_user_email(cart.user_id),
            subject=f"You left {item_count} tracks in your cart",
            body=f"""
You have {item_count} tracks waiting in your cart for ₹{totals['total']//100}.
{"You're saving ₹" + str(totals['discount']//100) + " with your cart discount!" if totals['discount'] > 0 else ""}

Complete your purchase: https://mixmint.site/cart

Your cart expires in {(cart.expires_at - timezone.now()).days} days.
            """
        )
        cart.reminder_sent = True
        cart.save()
```

---

## Admin Cart Analytics (Admin → Revenue Intelligence → Cart)

```
┌──────────────────────────────────────────────────────────────┐
│  CART ANALYTICS — March 2026                                │
│                                                              │
│  Carts created:      142                                    │
│  Carts purchased:     89  (63% conversion)                 │
│  Carts abandoned:     53  (37% abandonment)                │
│  Reminders sent:      41                                    │
│  Recovered from reminder: 12  (29% recovery rate)         │
│                                                              │
│  Discount usage:                                            │
│  3+ item carts:       34  ·  avg saving ₹24               │
│  5+ item carts:       18  ·  avg saving ₹67               │
│  10+ item carts:       4  ·  avg saving ₹180              │
│                                                              │
│  Avg cart size:       3.2 items                            │
│  Avg cart value:      ₹218                                 │
│  Total discount given: ₹4,320                              │
│  Revenue from carts:   ₹19,402                            │
└──────────────────────────────────────────────────────────────┘
```

---

## DB Schema (Complete)

```sql
CREATE TABLE carts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  status VARCHAR(20) DEFAULT 'active',
  discount_pct INTEGER DEFAULT 0,
  discount_amount INTEGER DEFAULT 0,
  subtotal INTEGER DEFAULT 0,
  total INTEGER DEFAULT 0,
  reminder_sent BOOLEAN DEFAULT FALSE,
  expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '30 days',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  purchased_at TIMESTAMPTZ
);

CREATE TABLE cart_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cart_id UUID REFERENCES carts(id) ON DELETE CASCADE,
  content_id UUID NOT NULL,
  content_type VARCHAR(10),
  dj_id UUID REFERENCES profiles(id),
  price INTEGER NOT NULL,   -- price at time of adding
  added_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(cart_id, content_id, content_type)
);

ALTER TABLE purchases
  ADD COLUMN cart_id UUID REFERENCES carts(id),
  ADD COLUMN original_price INTEGER,   -- price before discount
  ADD COLUMN discount_applied INTEGER DEFAULT 0,
  ADD COLUMN final_price INTEGER;      -- price after discount

CREATE TABLE cart_discount_tiers (
  id SERIAL PRIMARY KEY,
  min_items INTEGER,
  discount_pct DECIMAL(5,2),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default tiers
INSERT INTO cart_discount_tiers (min_items, discount_pct) VALUES
  (3, 10.00),
  (5, 15.00),
  (10, 20.00);
```

---

# ═══════════════════════════════════════════════════
# INTEGRATION NOTES — HOW ALL 3 FEATURES INTERACT
# ═══════════════════════════════════════════════════

```
Cart + External Links:
  External-link (free) tracks CANNOT be added to cart.
  They have no price and no checkout. Button = direct link.
  Cart only contains paid (non-external) tracks.

Cart + DJ Purchase:
  DJ adding another DJ's track to cart works normally.
  DJ's own tracks show [✓ Yours] badge — cannot add to cart.
  DJ's previously purchased tracks show [✓ Owned] — cannot re-add.

External Links + DJ Purchase:
  A DJ cannot purchase an external-link track (it's free).
  If a track was purchased paid and THEN converted to external,
  the buyer (DJ or regular) retains their purchase in their library
  pointing to the new external link.

Cart + Bundles (Feature 12):
  Bundles can be added to cart like any other item.
  Bundle counts as 1 item for discount tier calculation.
  (Not expanded to individual track count — prevents gaming)

Cart Discounts + Collaborations:
  Collab tracks: discount applied to final_price.
  Each collaborator's revenue is proportional to their % of
  the discounted final_price, same as normal collab split.
```

---

# ═══════════════════════════════════════════════════
# QA TEST CASES — ALL 3 FEATURES
# ═══════════════════════════════════════════════════

## Feature 01 — Underperforming Track Offload

```
Test ID  Scenario                              Expected          Fail Condition
────────────────────────────────────────────────────────────────────────────────
UPO-01   Track 61 days old, 0 sales           Flagged as        Not flagged
                                               underperforming
UPO-02   Track 29 days old, 0 sales           NOT flagged       Flagged (too new)
UPO-03   DJ clicks Convert, pastes GDrive link Validated ✓      Rejected incorrectly
UPO-04   DJ pastes Dropbox link               Rejected (not     Accepted
                                               allowed domain)
UPO-05   DJ pastes broken GDrive link         Error: not        Accepted
                                               accessible
UPO-06   Conversion complete — track page     Free badge +      Price still shown
                                               external button
UPO-07   Existing buyer's library             External link     Error or nothing
                                               shown
UPO-08   External link goes dead (cron)       DJ notified +     Silently broken
                                               broken badge
UPO-09   DJ updates broken link               New link saved,   Old link persists
                                               badge cleared
UPO-10   R2 file deleted after conversion     403 on direct     File still in R2
                                               access
```

## Feature 02 — DJ-to-DJ Purchase

```
Test ID  Scenario                              Expected          Fail Condition
────────────────────────────────────────────────────────────────────────────────
DJP-01   DJ views another DJ's track page     [Add to Cart]     Button missing
                                               and [Buy Now] shown
DJP-02   DJ attempts to buy own track         Error: own        Checkout proceeds
                                               content
DJP-03   DJ buys another DJ's track           Normal checkout   Error
                                               succeeds
DJP-04   Purchased track in DJ library        Shows in          Not visible
                                               /library
DJP-05   Selling DJ earnings updated          +85% of price     No update
DJP-06   Selling DJ notified                  "DJ Priya bought  No notification
                                               your track"
DJP-07   DJ re-attempts to buy owned track    Error: already    Re-purchase allowed
                                               owned
DJP-08   DJ earnings panel                    No change from    Shows as DJ earning
                                               purchase
DJP-09   Buyer type in selling DJ panel       ✦ DJ badge shown  No differentiation
```

## Feature 03 — Cart + Bulk Download + Discounts

```
Test ID  Scenario                              Expected          Fail Condition
────────────────────────────────────────────────────────────────────────────────
CART-01  Add 1 track to cart                  No discount       Discount shown
CART-02  Add 3 tracks to cart                 10% discount      No discount
CART-03  Add 5 tracks to cart                 15% discount      10% discount
CART-04  Add 10 tracks to cart                20% discount      15% discount
CART-05  Add own track to cart                Blocked           Added to cart
CART-06  Add already-owned track to cart      Blocked           Added to cart
CART-07  Add external-link track to cart      Blocked           Added to cart
CART-08  Cart with 3 items, checkout          Single payment    Multiple payments
                                               for total
CART-09  Bulk download page loads             All 3 tracks      Error
                                               listed
CART-10  Download from bulk page              Token system      Bypasses token
                                               used normally
CART-11  Guest adds to cart, logs in          Cart merged       Guest cart lost
CART-12  Cart abandoned 3 days               Reminder email    No email
CART-13  Cart expires after 30 days           Items cleared,    Stays forever
                                               user notified
CART-14  Discount distribution to 2 DJs       Each DJ gets      All discount from
          in same cart                         proportional cut  one DJ
CART-15  Cart max 20 items                    21st item blocked Added
CART-16  Remove item from cart               Cart recalculates  Stale price
CART-17  PhonePe payment fails on cart        Cart not marked   Cart marked
                                               purchased         purchased
CART-18  Collab track in cart (3 items)       Collab DJ         Only lead DJ
                                               revenue split     gets revenue
                                               applies
```

---

*End of Three New Features Prompt*
*Feature 01: Underperforming Track Offload · Feature 02: DJ-to-DJ Purchase*
*Feature 03: Cart + Bulk Download + Discount Offers*
