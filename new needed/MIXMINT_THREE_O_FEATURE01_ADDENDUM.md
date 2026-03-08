# 🎛️ MIXMINT — FEATURE 01 ADDENDUM
### *Free Tracks: Same External Link Offload Rule*
### *Extends: MIXMINT_THREE_NEW_FEATURES.md — Feature 01*

---

## WHAT CHANGES

Feature 01 originally covered **paid underperforming tracks only**.

This addendum extends the same offload system to **all free tracks** —
whether they were always free (price = ₹0) or converted to free later.

---

## THE NEW RULE

```
Any track or album where price = ₹0:

  Option A (current — costs DJ storage):
    File stays in R2, served via MixMint token system,
    buyer clicks Download → token → Cloudflare Worker → file

  Option B (new — zero storage cost):
    DJ uploads file to Google Drive or MediaFire,
    pastes public link in MixMint,
    MixMint replaces Download button with external redirect,
    R2 file deleted (storage reclaimed)

Option B is offered to DJs at two moments:
  1. When DJ sets a track price to ₹0 (free) — prompt shown immediately
  2. Weekly cron — detects existing free tracks still on R2 storage
     and sends DJ a digest suggesting offload
```

---

## LOGIC CHANGE — Detection Cron Update

```python
def detect_offload_candidates():
    """
    Extended cron — now catches BOTH:
    1. Underperforming paid tracks (original Feature 01 logic)
    2. ALL free tracks still hosted on R2 (new)
    """
    too_new = timezone.now() - timedelta(days=7)
    # Free tracks only need 7 days before suggesting offload
    # (unlike 30 days for paid — free tracks have no sales to wait for)

    # --- PAID UNDERPERFORMING (unchanged) ---
    paid_underperforming = Track.objects.filter(
        is_active=True,
        is_deleted=False,
        is_external_link=False,
        file_status='ready',
        price__gt=0,
        created_at__lt=timezone.now() - timedelta(days=30)
    ).annotate(
        sales_in_period=Count(
            'purchases',
            filter=Q(
                purchases__created_at__gte=timezone.now() - timedelta(days=90),
                purchases__download_completed=True,
                purchases__status='active'
            )
        )
    ).filter(sales_in_period__lt=settings.UNDERPERFORM_SALES_THRESHOLD)

    # --- FREE TRACKS ON R2 (new) ---
    free_on_r2 = Track.objects.filter(
        is_active=True,
        is_deleted=False,
        is_external_link=False,   # still on MixMint storage
        file_status='ready',
        price=0,                  # free tracks
        created_at__lt=too_new    # at least 7 days old
    )

    # Same for albums
    free_albums_on_r2 = Album.objects.filter(
        is_active=True,
        is_deleted=False,
        is_external_link=False,
        file_status='ready',
        price=0,
        created_at__lt=too_new
    )

    # Combine and notify
    all_candidates = list(paid_underperforming) + \
                     list(free_on_r2) + \
                     list(free_albums_on_r2)

    notified_djs = set()
    for content in all_candidates:
        already_notified = OffloadNotification.objects.filter(
            content_id=content.id,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).exists()
        if already_notified:
            continue

        OffloadNotification.objects.create(
            dj_id=content.dj_id,
            content_id=content.id,
            content_type='track' if isinstance(content, Track) else 'album',
            reason='free_on_r2' if content.price == 0 else 'underperforming',
            storage_mb=content.file_size_bytes // (1024 * 1024)
        )
        notified_djs.add(content.dj_id)

    for dj_id in notified_djs:
        send_offload_digest_email(dj_id)
```

---

## EMAIL — Free Track Version

DJ receives a separate section in their offload digest email for free tracks:

```
Subject: Save storage — move your free tracks to Google Drive

Hi DJ Rohit,

Your free tracks are taking up MixMint storage for no reason.
Move them to Google Drive or MediaFire and we'll serve the
download link instead — zero cost to you, zero storage used.

Free tracks on MixMint storage:
  · Intro Mix (Free) — 24 MB
  · Promo Set 2024 (Free) — 118 MB
  · Teaser Track (Free) — 8 MB

Total storage you can reclaim: 150 MB

Move them here: https://mixmint.site/dj-panel/tracks?tab=offload

— MixMint Team

P.S. Your buyers still get the same free download experience.
Nothing changes for them — the link just comes from Google Drive.
```

---

## WHEN DJ SETS A TRACK TO FREE (Price = ₹0) — Immediate Prompt

When a DJ edits a track and sets price to ₹0 (or uploads a new track as free):

```
┌──────────────────────────────────────────────────────────────┐
│  Track set to Free                                          │
│                                                              │
│  Since this track is free, you can host it on Google Drive  │
│  or MediaFire instead of using your MixMint storage.       │
│                                                              │
│  This saves your storage quota and costs you nothing extra. │
│                                                              │
│  [Host on External Link →]    [Keep on MixMint Storage]    │
│                                                              │
│  You can always change this later in track settings.       │
└──────────────────────────────────────────────────────────────┘
```

- If DJ picks [Host on External Link →] → opens the same 3-step flow from Feature 01
- If DJ picks [Keep on MixMint Storage] → proceeds normally, no further prompts for 30 days

---

## DJ DASHBOARD — Offload Tab (Updated)

`DJ Panel → My Tracks → Offload` tab now shows two sections:

```
┌──────────────────────────────────────────────────────────────┐
│  STORAGE OFFLOAD                                            │
│                                                              │
│  Total storage you can reclaim:  1.2 GB                    │
│                                                              │
│  ── FREE TRACKS ON MIXMINT STORAGE ─────────────────────   │
│  These are free — no reason to use your storage quota.    │
│                                                              │
│  🎵 Intro Mix                    Free  ·  24 MB            │
│  [Move to External Link →]                                  │
│                                                              │
│  📦 Promo Set 2024               Free  ·  118 MB           │
│  [Move to External Link →]                                  │
│                                                              │
│  ── UNDERPERFORMING PAID TRACKS ────────────────────────   │
│  Low sales — consider converting to free external download  │
│                                                              │
│  🎵 Deep Blue (Extended Mix)     ₹49  ·  0 sales / 90d    │
│  [Keep as Paid]  [Convert to Free External Link →]         │
└──────────────────────────────────────────────────────────────┘
```

---

## PUBLIC TRACK PAGE — Free External Link State

Same as the paid → external link state, but the badge already says FREE:

```
┌──────────────────────────────────────────────────────────────┐
│  Intro Mix                                                  │
│  DJ Rohit · Promo · 4:12                                   │
│                                                              │
│  FREE                                                        │
│  [⬇  Free Download  ↗]   ← opens Google Drive / MediaFire  │
│  Hosted on Google Drive                                     │
│                                                              │
│  [YouTube preview]                                         │
└──────────────────────────────────────────────────────────────┘
```

No login required. No token. No attempt count. Just a redirect.

---

## DOWNLOAD BUTTON LOGIC (UPDATED — ALL CASES)

```python
def get_download_button_config(track, user):
    """
    Returns what button to show on track/album page.
    Now covers all 4 states.
    """

    # STATE 1: External link (free, hosted externally)
    if track.is_external_link:
        return {
            'type': 'external_redirect',
            'label': 'Free Download ↗',
            'url': track.external_link_url,
            'provider': track.external_link_provider,
            'requires_login': False,
            'price': 0
        }

    # STATE 2: Free, still on MixMint R2
    if track.price == 0:
        if not user.is_authenticated:
            return {
                'type': 'login_to_download',
                'label': 'Login to Download Free',
                'requires_login': True,
                'price': 0
            }
        # Free but needs login — go through token system
        return {
            'type': 'free_token_download',
            'label': 'Download Free',
            'requires_login': True,
            'price': 0
        }

    # STATE 3: Paid, user already owns it
    if user.is_authenticated and user_owns(user.id, track.id):
        return {
            'type': 'redownload',
            'label': 'Download Again',
            'requires_login': True,
            'redownload_price': track.price // 2
        }

    # STATE 4: Paid, user doesn't own it
    return {
        'type': 'purchase',
        'label': f'Buy & Download',
        'price': track.price,
        'requires_login': True
    }
```

---

## KEY DIFFERENCE: FREE ON R2 VS FREE EXTERNAL

```
Free on R2 (before offload):
  · Requires login to download
  · Goes through token system
  · Counts against DJ storage quota
  · 3 attempt limit applies
  · Device/IP binding applies

Free External Link (after offload):
  · No login required
  · No token — direct redirect
  · Zero storage cost to DJ
  · No attempt limit (not our server)
  · No device/IP binding
  · File served by Google/MediaFire
```

For DJs: external is always better for free tracks — no cost, no limit.
For buyers: external is slightly less secure but it's free content anyway.

---

## DB SCHEMA ADDITION

```sql
-- Add reason column to offload notification table
ALTER TABLE underperform_notifications
  RENAME TO offload_notifications;

ALTER TABLE offload_notifications
  ADD COLUMN reason VARCHAR(20) DEFAULT 'underperforming',
    -- 'underperforming' | 'free_on_r2'
  ADD COLUMN storage_mb INTEGER;

-- Track/Album tables already have is_external_link, external_link_url
-- No new columns needed — price=0 + is_external_link=true = free external
```

---

## QA TEST CASES — FREE TRACK OFFLOAD

```
Test ID  Scenario                              Expected           Fail
───────────────────────────────────────────────────────────────────────
FTO-01   DJ sets track to free, prompt shown   Offload prompt     No prompt
FTO-02   DJ dismisses prompt                   No prompt 30 days  Prompt again
FTO-03   Cron: free track on R2, 8 days old    Flagged            Not flagged
FTO-04   Cron: free track on R2, 5 days old    NOT flagged        Flagged
FTO-05   DJ offloads free track to GDrive      External button    Still token button
FTO-06   Buyer downloads free external link    No login needed,   Requires login
                                               redirect works
FTO-07   Free external track — attempt count   Not tracked        Attempt error
FTO-08   Free on R2 — attempt count            Tracked (3 max)    Not tracked
FTO-09   DJ storage count after free offload   Reduced correctly  Unchanged
FTO-10   Public page — free external label     "Hosted on         No provider shown
                                               Google Drive"
FTO-11   Free external + broken link           Warning badge,     Silent failure
                                               DJ notified
FTO-12   Free track offload digest email       Groups free +      Mixed together
                                               underperforming    confusingly
                                               in separate sections
```

---

*End of Feature 01 Addendum*
*Free tracks follow identical offload path — GDrive/MediaFire external link*
*Zero storage cost · No token system · No login required · No attempt limits*
