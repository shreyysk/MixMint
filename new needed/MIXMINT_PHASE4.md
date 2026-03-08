# 🎛️ MIXMINT — MISSING ITEMS SPEC
### *5 gaps found by cross-checking original MIXMINT_2_0.docx against all 3 phases*
### *Add these to Phase 1 (items 1–4) and Phase 2 (item 5)*

---

## SUMMARY OF GAPS

```
❌  Popular this week filter       → Add to Phase 1 (Search)
❌  Dynamic ad floor pricing       → Add to Phase 2 (Admin)
❌  Hard IP/device blacklist       → Add to Phase 1 (Security)
❌  High-value transaction alerts  → Add to Phase 1 (Admin)
❌  Hold earnings/payouts          → Add to Phase 1 (Admin)
```

All 5 are either already implied by other systems but never fully
specified, or genuinely missing. Each is fully specced below.

---

# MISSING ITEM 01 — "POPULAR THIS WEEK" SEARCH FILTER

## Phase: 1 (add to Search Infrastructure — Gap 08)

## What It Is
A sort option in search and browse that ranks tracks by sales velocity in the last 7 days. Different from "relevance" (text match) — purely a trending signal.

---

## Implementation

```python
def get_popular_this_week(genre=None, limit=20, offset=0):
    """
    Tracks ranked by download completions in last 7 days.
    Only completed downloads count — not just purchases.
    """
    since = timezone.now() - timedelta(days=7)

    qs = Track.objects.filter(
        is_active=True,
        is_deleted=False,
        file_status='ready'
    ).annotate(
        weekly_sales=Count(
            'purchases',
            filter=Q(
                purchases__created_at__gte=since,
                purchases__download_completed=True,
                purchases__status='active'
            )
        )
    ).filter(
        weekly_sales__gt=0  # Only tracks with actual sales
    ).order_by('-weekly_sales', '-created_at')

    if genre:
        qs = qs.filter(genre__iexact=genre)

    return qs[offset:offset + limit]
```

---

## Search API — Sort Parameter

```python
def search_api(request):
    sort = request.GET.get('sort', 'relevance')
    # sort options: 'relevance' | 'popular' | 'new' | 'price_low' | 'price_high'

    if sort == 'popular':
        results = get_popular_this_week(
            genre=request.GET.get('genre'),
            limit=20,
            offset=(int(request.GET.get('page', 1)) - 1) * 20
        )
    elif sort == 'new':
        results = Track.objects.filter(
            is_active=True, is_deleted=False, file_status='ready'
        ).order_by('-created_at')
    else:
        results = search_tracks(
            query=request.GET.get('q', ''),
            filters=build_filters(request)
        )

    return JsonResponse({
        'results': [serialize_track(t) for t in results],
        'sort': sort
    })
```

---

## UI — Sort/Filter Bar (Browse + Search Pages)

```
Sort by:
[Relevance ▾]  options: Relevance · Popular This Week · New Releases · Price ↑ · Price ↓

Filter by genre:
[All] [House] [Techno] [Bollywood] [EDM] [Hip-Hop] [Afrobeats] [Other]
```

---

## Homepage — "Popular This Week" Section

```
┌──────────────────────────────────────────────────────────────┐
│  🔥  POPULAR THIS WEEK                    [View All →]      │
│                                                              │
│  [Track Card] [Track Card] [Track Card] [Track Card]        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

- Show top 4 tracks by weekly sales on homepage
- Cached hourly (not real-time — too expensive per page load)
- "View All →" links to `/browse?sort=popular`

---

## DB — Weekly Sales Denormalization (Performance)

```sql
-- Recalculate every hour via cron — avoids heavy COUNT on every page load
ALTER TABLE tracks ADD COLUMN sales_last_7_days INTEGER DEFAULT 0;

-- Cron job: /api/cron/update-weekly-sales (runs hourly)
UPDATE tracks SET sales_last_7_days = (
  SELECT COUNT(*)
  FROM purchases p
  WHERE p.content_id = tracks.id
    AND p.download_completed = TRUE
    AND p.status = 'active'
    AND p.created_at >= NOW() - INTERVAL '7 days'
);
```

---
---

# MISSING ITEM 02 — DYNAMIC AD FLOOR PRICING

## Phase: 2 (add to Ad System — Gap 01)

## What It Is
Higher-traffic DJs generate higher minimum bids on their ad inventory. A DJ with 500 weekly visitors gets higher CPM than a DJ with 50. Admin can set the floor formula.

---

## How It Works

```
Ad Floor Pricing Logic:

Base floor (all DJs):         ₹0.50 CPM (admin-set)
Traffic multiplier:           Weekly page views × multiplier

Tiers (admin-configurable):
  0–100 weekly views:         1.0× (base floor)
  101–500 weekly views:       1.5× floor
  501–2000 weekly views:      2.5× floor
  2000+ weekly views:         4.0× floor

Example:
  DJ Rohit → 800 weekly views → 2.5× → ₹1.25 CPM floor
  DJ Priya → 50 weekly views  → 1.0× → ₹0.50 CPM floor
```

---

## Tracking Weekly Page Views Per DJ

```python
def record_dj_page_view(dj_id, page_type):
    """
    Called on every storefront or track page load.
    Lightweight — fire and forget.
    """
    today = timezone.now().date()

    DJPageView.objects.update_or_create(
        dj_id=dj_id,
        date=today,
        defaults={}
    )
    # Use Redis counter for performance if available
    # Fall back to DB increment
    DJPageView.objects.filter(
        dj_id=dj_id, date=today
    ).update(view_count=F('view_count') + 1)


def get_weekly_views(dj_id):
    since = timezone.now().date() - timedelta(days=7)
    return DJPageView.objects.filter(
        dj_id=dj_id,
        date__gte=since
    ).aggregate(total=Sum('view_count'))['total'] or 0


def calculate_ad_floor(dj_id):
    """Calculate this DJ's current ad floor CPM in paise"""
    views = get_weekly_views(dj_id)
    base_floor = settings.AD_BASE_FLOOR_PAISE  # e.g. 50 paise

    tiers = settings.AD_FLOOR_TIERS
    # [(max_views, multiplier), ...]
    # e.g. [(100, 1.0), (500, 1.5), (2000, 2.5), (999999, 4.0)]

    multiplier = 1.0
    for max_views, tier_multiplier in sorted(tiers):
        if views <= max_views:
            multiplier = tier_multiplier
            break

    floor = int(base_floor * multiplier)

    # Cache per DJ (1 hour)
    cache.set(f"ad_floor_{dj_id}", floor, 3600)
    return floor
```

---

## Admin Controls (Add to Ad System section)

```
┌──────────────────────────────────────────────────────────────┐
│  DYNAMIC AD FLOOR PRICING                                   │
│                                                              │
│  Base floor CPM:  ₹[ 0.50 ] per 1000 impressions          │
│                                                              │
│  Traffic Tiers:                                             │
│  0 – 100 views/week:    [ 1.0 ]× multiplier → ₹0.50 CPM  │
│  101 – 500 views/week:  [ 1.5 ]× multiplier → ₹0.75 CPM  │
│  501 – 2000 views/week: [ 2.5 ]× multiplier → ₹1.25 CPM  │
│  2000+ views/week:      [ 4.0 ]× multiplier → ₹2.00 CPM  │
│                                                              │
│  [Save Floor Settings]                                      │
│                                                              │
│  Top DJs by weekly views:                                   │
│  DJ Rohit   · 1,240 views · Floor: ₹1.25 CPM              │
│  DJ Priya   · 890 views   · Floor: ₹1.25 CPM              │
│  DJ Arjun   · 320 views   · Floor: ₹0.75 CPM              │
└──────────────────────────────────────────────────────────────┘
```

---

## How Floor Price is Used with AdSense

Google AdSense doesn't directly accept per-DJ floor prices via API at standard tier. Practical implementation:

```
Option A (Simple — launch):
  Set one global floor price in AdSense dashboard.
  Use traffic tier data internally to:
  - Report to admin which DJs are generating high CPM
  - Use as negotiating data for direct advertisers later
  - Show admin intelligence: "top 5 DJs generating 60% of ad revenue"

Option B (Advanced — post launch):
  Use Google Ad Manager (GAM) for floor price control per page.
  GAM allows programmatic floor rules.
  Integrate when platform reaches 50,000+ monthly pageviews.
```

**Launch with Option A — store the data, use it for reporting.**

---

## DB Schema

```sql
CREATE TABLE dj_page_views (
  dj_id UUID REFERENCES profiles(id),
  date DATE,
  view_count INTEGER DEFAULT 0,
  PRIMARY KEY (dj_id, date)
);

ALTER TABLE profiles
  ADD COLUMN weekly_views INTEGER DEFAULT 0,
  ADD COLUMN ad_floor_cpm INTEGER DEFAULT 50;  -- in paise

-- Hourly cron updates this for fast reads
-- /api/cron/update-ad-floors
```

---
---

# MISSING ITEM 03 — HARD IP / DEVICE BLACKLIST

## Phase: 1 (add to Security — after Fraud Detection)

## What It Is
Admin-maintained list of IP addresses and device fingerprints that are permanently blocked from the platform. Different from fraud detection (which is reactive) — this is manual/permanent admin action.

---

## Block Types

```
IP Blacklist:      Block all requests from a specific IP address
                   Use case: known pirate IPs, VPN exit nodes, scrapers
                   Scope: global (affects all users from that IP)

Device Blacklist:  Block a specific device fingerprint
                   Use case: repeat abuse from a device even after
                   creating new accounts
                   Scope: global

CIDR Block:        Block an entire IP range (e.g. 192.168.1.0/24)
                   Use case: bot farms, datacenter IP ranges
                   Scope: global
```

---

## Admin Blacklist Panel (Admin → Security → IP & Device Blacklist)

```
┌──────────────────────────────────────────────────────────────┐
│  IP & DEVICE BLACKLIST                                      │
│                                                              │
│  Add to blacklist:                                          │
│  Type: [IP Address ▾]  (IP Address / CIDR Range / Device)  │
│  Value: [___________________]                               │
│  Reason: [___________________]  (internal note)            │
│  [Add to Blacklist]                                         │
│                                                              │
│  Active Blacklist:                                          │
│  Type    Value              Reason          Added    Action │
│  ────────────────────────────────────────────────────────  │
│  IP      103.21.x.x        Scraper         2d ago   [✕]   │
│  CIDR    45.33.0.0/16      Bot farm        5d ago   [✕]   │
│  Device  a3f8c2...         Repeat fraud    1d ago   [✕]   │
│                                                              │
│  Total blocked: 12 IPs · 3 CIDRs · 7 devices              │
└──────────────────────────────────────────────────────────────┘
```

---

## Enforcement Middleware

```python
import ipaddress

# Cache blacklist in memory (refresh every 5 minutes)
# Avoids DB hit on every request

def get_blacklist():
    cached = cache.get('ip_blacklist')
    if cached:
        return cached

    ips = set(IPBlacklist.objects.filter(
        type='ip', is_active=True
    ).values_list('value', flat=True))

    cidrs = [
        ipaddress.ip_network(cidr, strict=False)
        for cidr in IPBlacklist.objects.filter(
            type='cidr', is_active=True
        ).values_list('value', flat=True)
    ]

    devices = set(IPBlacklist.objects.filter(
        type='device', is_active=True
    ).values_list('value', flat=True))

    blacklist = {'ips': ips, 'cidrs': cidrs, 'devices': devices}
    cache.set('ip_blacklist', blacklist, 300)  # 5 min cache
    return blacklist


class BlacklistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = get_client_ip(request)
        device = request.headers.get('X-Device-Fingerprint', '')
        blacklist = get_blacklist()

        # Check exact IP
        if ip in blacklist['ips']:
            return HttpResponse('Access denied', status=403)

        # Check CIDR ranges
        try:
            ip_obj = ipaddress.ip_address(ip)
            for cidr in blacklist['cidrs']:
                if ip_obj in cidr:
                    return HttpResponse('Access denied', status=403)
        except ValueError:
            pass

        # Check device
        if device and device in blacklist['devices']:
            return HttpResponse('Access denied', status=403)

        return self.get_response(request)
```

---

## Auto-Add to Blacklist (From Fraud System)

```python
# When fraud score >= 90 → auto-add IP to blacklist
def handle_severe_fraud(user_id, ip, device, flags):
    if 'ip_account_farm' in flags:
        IPBlacklist.objects.get_or_create(
            type='ip',
            value=ip,
            defaults={
                'reason': f'Auto: ip_account_farm detected',
                'added_by': 'system'
            }
        )
        cache.delete('ip_blacklist')  # Force refresh
        send_admin_alert(f"IP auto-blacklisted: {ip}", flags)
```

---

## DB Schema

```sql
CREATE TABLE ip_blacklist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type VARCHAR(10),      -- 'ip' | 'cidr' | 'device'
  value VARCHAR(100),    -- IP, CIDR string, or device hash
  reason TEXT,
  added_by UUID REFERENCES profiles(id),  -- NULL = system auto-add
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(type, value)
);
```

---
---

# MISSING ITEM 04 — HIGH-VALUE TRANSACTION ALERTS

## Phase: 1 (add to Admin Controls)

## What It Is
Admin receives an immediate alert when an unusually large purchase is made. Protects against stolen card fraud before chargeback arrives.

---

## Alert Thresholds (Admin-Configurable)

```
Admin → Security → Transaction Alerts

Single transaction threshold:   ₹[ 500 ]   → alert admin
Same user, 3 purchases in 1hr:  Total ₹[ 300 ]   → alert admin
Same card, 2+ purchases:        Any amount → alert admin
New account, high value:        Account <24h, ₹[ 200 ]+ → alert admin
```

---

## Implementation

```python
HIGH_VALUE_THRESHOLD_PAISE = 50000  # ₹500

def check_high_value_transaction(purchase):
    alerts = []
    user_id = purchase.user_id
    amount = purchase.original_price

    # Alert 1: Single high-value transaction
    if amount >= settings.HIGH_VALUE_THRESHOLD_PAISE:
        alerts.append({
            'type': 'high_value_single',
            'message': f'Single purchase of ₹{amount//100} by user {user_id}',
            'severity': 'HIGH'
        })

    # Alert 2: Velocity — 3+ purchases in 1 hour
    recent_count = Purchase.objects.filter(
        user_id=user_id,
        created_at__gte=timezone.now() - timedelta(hours=1),
        status__in=['active', 'pending']
    ).count()
    if recent_count >= 3:
        recent_total = Purchase.objects.filter(
            user_id=user_id,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).aggregate(total=Sum('original_price'))['total'] or 0
        if recent_total >= settings.HIGH_VALUE_VELOCITY_THRESHOLD:
            alerts.append({
                'type': 'high_velocity',
                'message': f'{recent_count} purchases totalling ₹{recent_total//100} in 1hr',
                'severity': 'HIGH'
            })

    # Alert 3: New account buying high value
    profile = Profile.objects.get(id=user_id)
    account_age_hours = (timezone.now() - profile.created_at).total_seconds() / 3600
    if account_age_hours < 24 and amount >= 20000:  # ₹200+
        alerts.append({
            'type': 'new_account_high_value',
            'message': f'New account (<24h) purchase of ₹{amount//100}',
            'severity': 'MEDIUM'
        })

    for alert in alerts:
        # Save to DB
        TransactionAlert.objects.create(
            purchase_id=purchase.id,
            user_id=user_id,
            alert_type=alert['type'],
            message=alert['message'],
            severity=alert['severity']
        )
        # Email admin immediately for HIGH severity
        if alert['severity'] == 'HIGH':
            send_admin_transaction_alert(purchase, alert)


def send_admin_transaction_alert(purchase, alert):
    send_email(
        to=settings.ADMIN_ALERT_EMAIL,
        subject=f"⚠️ MixMint Transaction Alert — {alert['type']}",
        body=f"""
High-value transaction detected.

Alert type: {alert['type']}
Severity: {alert['severity']}
Message: {alert['message']}

Purchase ID: {purchase.id}
User ID: {purchase.user_id}
Amount: ₹{purchase.original_price // 100}
Track: {purchase.content_id}
Time: {timezone.now().isoformat()}

Review: https://mixmint.site/admin/transactions/{purchase.id}
        """
    )
```

---

## Admin Alerts Dashboard (Admin → Security → Transaction Alerts)

```
┌──────────────────────────────────────────────────────────────┐
│  TRANSACTION ALERTS                                         │
│                                                              │
│  Unreviewed: 3  ·  This week: 8  ·  Total: 47             │
│                                                              │
│  Alert Thresholds:                                          │
│  Single tx > ₹[ 500 ]  ·  Velocity 3 in 1hr > ₹[ 300 ]  │
│  New account > ₹[ 200 ]     [Save]                         │
│                                                              │
│  Recent Alerts:                                             │
│  Type              User      Amount   Time      Action     │
│  ─────────────────────────────────────────────────────     │
│  🔴 high_value     user_x    ₹800     5min ago  [Review]  │
│  🟡 new_acct       user_y    ₹350     1hr ago   [Review]  │
│  🔴 high_velocity  user_z    ₹600     2hr ago   [Resolved]│
│                                                              │
│  Actions: [Mark Safe] [Freeze Account] [Refund & Block]    │
└──────────────────────────────────────────────────────────────┘
```

---

## DB Schema

```sql
CREATE TABLE transaction_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  purchase_id UUID REFERENCES purchases(id),
  user_id UUID REFERENCES profiles(id),
  alert_type VARCHAR(50),
  message TEXT,
  severity VARCHAR(10),  -- 'HIGH' | 'MEDIUM' | 'LOW'
  reviewed BOOLEAN DEFAULT FALSE,
  reviewed_by UUID REFERENCES profiles(id),
  outcome VARCHAR(30),   -- 'safe' | 'frozen' | 'refunded_blocked'
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---
---

# MISSING ITEM 05 — HOLD EARNINGS / PAYOUTS (ADMIN CONTROL)

## Phase: 1 (add to Payout Engine)

## What It Is
Admin can freeze a specific DJ's pending earnings — preventing payout — for legal review, suspected fraud, chargeback protection, or dispute resolution. Already referenced in original spec but never fully implemented.

---

## Hold Types

```
Type                Scope                   Duration
──────────────────────────────────────────────────────────────
legal_review        All earnings frozen     Until admin releases
chargeback          Specific amount frozen  Until chargeback resolved
dispute             Specific purchase amt   Until dispute resolved
fraud_investigation All earnings frozen     Until investigation done
admin_manual        Admin discretion        Admin sets manually
```

---

## Admin — Hold Controls (per DJ, in DJ detail page)

```
┌──────────────────────────────────────────────────────────────┐
│  Earnings Hold — DJ Rohit                                   │
│                                                              │
│  Current wallet:                                            │
│  Pending earnings:     ₹4,200                              │
│  Held (escrow):        ₹800                                │
│  Available for payout: ₹3,400                              │
│                                                              │
│  Place Hold:                                               │
│  Type:    [Legal Review ▾]                                 │
│  Amount:  ● Hold all pending  ○ Hold ₹[_____] only        │
│  Reason:  [Internal note — not shown to DJ]                │
│  Notify DJ: [✓] Send hold notification email              │
│  [Place Hold]                                               │
│                                                              │
│  Active Holds:                                              │
│  ₹800  · chargeback  · placed 3d ago  [Release] [Forfeit] │
└──────────────────────────────────────────────────────────────┘
```

---

## Implementation

```python
def place_earnings_hold(dj_id, hold_type, amount=None,
                        reason='', admin_id=None, notify_dj=True):
    """
    amount=None means hold ALL pending earnings.
    """
    wallet = DJWallet.objects.select_for_update().get(dj_id=dj_id)

    hold_amount = amount or wallet.pending_earnings

    if hold_amount > wallet.pending_earnings:
        raise ValueError("Hold amount exceeds pending earnings")

    with transaction.atomic():
        # Move from pending to escrow
        wallet.pending_earnings -= hold_amount
        wallet.escrow_amount += hold_amount
        wallet.save()

        EarningsHold.objects.create(
            dj_id=dj_id,
            amount=hold_amount,
            hold_type=hold_type,
            reason=reason,
            placed_by=admin_id,
            status='active'
        )

    if notify_dj:
        send_earnings_hold_email(dj_id, hold_amount, hold_type)

    # Log for audit
    AdminAuditLog.objects.create(
        admin_id=admin_id,
        action='place_earnings_hold',
        target_dj_id=dj_id,
        details={
            'amount': hold_amount,
            'type': hold_type,
            'reason': reason
        }
    )


def release_earnings_hold(hold_id, admin_id, outcome='released'):
    """
    outcome: 'released' (back to DJ) | 'forfeited' (kept by platform)
    """
    hold = EarningsHold.objects.get(id=hold_id, status='active')
    wallet = DJWallet.objects.select_for_update().get(dj_id=hold.dj_id)

    with transaction.atomic():
        wallet.escrow_amount -= hold.amount

        if outcome == 'released':
            wallet.pending_earnings += hold.amount
            wallet.save()
            send_earnings_released_email(hold.dj_id, hold.amount)
        else:  # forfeited
            wallet.save()
            # Platform keeps the money — log it
            PlatformRevenue.objects.create(
                source='forfeited_hold',
                amount=hold.amount,
                dj_id=hold.dj_id,
                hold_id=hold.id
            )

        hold.status = outcome
        hold.resolved_by = admin_id
        hold.resolved_at = timezone.now()
        hold.save()
```

---

## Payout Processing — Respects Holds

```python
def process_weekly_payouts():
    eligible_djs = DJWallet.objects.filter(
        pending_earnings__gte=settings.PAYOUT_THRESHOLD,  # ₹500
    ).select_related('profile')

    for wallet in eligible_djs:
        dj = wallet.profile

        # Skip if payout is globally frozen by admin
        if dj.payout_frozen:
            continue

        # Only pay out what's NOT in escrow
        # pending_earnings is already net of escrow (see place_hold above)
        payout_amount = wallet.pending_earnings

        if payout_amount < settings.PAYOUT_THRESHOLD:
            continue

        # Calculate TDS if applicable
        payout_data = calculate_payout_with_tds(dj.id, payout_amount)

        # Process via PhonePe
        process_dj_payout(
            dj_id=dj.id,
            gross=payout_data['gross'],
            tds=payout_data['tds_deducted'],
            net=payout_data['net_payout']
        )
```

---

## DJ View — Held Earnings Notice

In DJ Dashboard → Earnings, if any earnings are in hold:

```
┌──────────────────────────────────────────────────────┐
│  ⚠️  Some earnings are currently on hold           │
│                                                      │
│  ₹800 is under review by MixMint.                  │
│  You will be notified once resolved.                │
│  Questions? support@mixmint.site                   │
└──────────────────────────────────────────────────────┘
```

- DJ sees the held amount and that it's "under review"
- DJ does NOT see the internal reason (admin note is private)
- DJ sees support email to contact if needed

---

## DB Schema

```sql
CREATE TABLE earnings_holds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dj_id UUID REFERENCES profiles(id),
  amount INTEGER,           -- in paise
  hold_type VARCHAR(30),    -- 'legal_review' | 'chargeback' |
                            -- 'dispute' | 'fraud_investigation' | 'admin_manual'
  reason TEXT,              -- internal admin note, never shown to DJ
  status VARCHAR(20) DEFAULT 'active',
    -- 'active' | 'released' | 'forfeited'
  placed_by UUID REFERENCES profiles(id),
  resolved_by UUID REFERENCES profiles(id),
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE profiles
  ADD COLUMN payout_frozen BOOLEAN DEFAULT FALSE;
  -- Global payout freeze for this DJ (separate from specific holds)

CREATE TABLE admin_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_id UUID REFERENCES profiles(id),
  action VARCHAR(100),
  target_dj_id UUID REFERENCES profiles(id),
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
-- Immutable audit trail of all admin financial actions
```

---

# FINAL VERDICT — ARE THE 3 PHASES COMPLETE NOW?

```
After adding these 5 missing items:

✅  Every feature in MIXMINT_2_0.docx is covered
✅  Every fix from all sessions is covered
✅  Every infrastructure gap is covered
✅  Every compliance requirement is covered
✅  Every growth feature is covered

The only things not in these documents:
  → UI/UX visual design (separate UIUX prompt document)
  → Actual code implementation (that's what you build with these prompts)
  → Third-party API credentials (PhonePe, AdSense, R2 keys)
  → Your specific domain, branding, color values (in UIUX doc)

WHERE TO ADD THESE 5 ITEMS:
  Items 01, 03, 04, 05 → Phase 1 (MIXMINT_PHASE1_FOUNDATION.md)
  Item 02              → Phase 2 (MIXMINT_PHASE2_OPERATIONS.md)
```

---

*End of Missing Items Spec*
*5 gaps closed · Original spec 100% covered across 3 phases*
