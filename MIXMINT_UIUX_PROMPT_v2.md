# 🎛️ MIXMINT — ULTRA-DETAILED UI/UX DESIGN PROMPT (v2)
### *"Home of DJ Releases" — India's Most Secure DJ Music Marketplace*

---

## ⚡ DESIGN IDENTITY & AESTHETIC DIRECTION

**Aesthetic:** **Dark Luxury Brutalism** (dark mode) / **Warm Editorial Cream** (light mode)
Not a generic music app. Not Spotify. Not Bandcamp. MixMint is a *vault* — where DJs sell ownership, not streams. The design must feel handcrafted, intentional, and slightly raw. No rounded-everything. No gradient purple. No Inter font. No AI-slop card layouts. Every element should feel like it was made by a designer who knows what a DJ booth looks like.

**Design Anti-Patterns to Avoid:**
- No glassmorphism blobs everywhere
- No purple-on-white AI gradients
- No emoji-stuffed section headers in actual UI
- No cookie-cutter SaaS dashboard layouts
- No Spotify-clone dark sidebar with playlist rows
- No rounded pill buttons on everything — mix sharp and rounded intentionally

---

## 🎨 DUAL THEME SYSTEM

### Theme Switching Behavior
- **Auto-detect:** On first visit, respect `prefers-color-scheme` (OS setting)
- **Manual override:** Sun/Moon icon toggle in navbar, top-right
- **Persistence:** Store preference in `localStorage` key `mm-theme`
- **Transition:** `transition: background-color 0.3s ease, color 0.3s ease` on `:root` — smooth, no flash
- **CSS approach:** CSS custom properties on `:root[data-theme="dark"]` and `:root[data-theme="light"]`

---

### 🌑 DARK THEME TOKENS

```
--bg-base:        #0A0A0F   (page background, near-black)
--bg-surface:     #111118   (cards, panels)
--bg-elevated:    #1A1A25   (modals, dropdowns)
--border:         rgba(255,255,255,0.06)
--border-focus:   #00FFB3
--text-primary:   #F0F0F5
--text-muted:     #6B6B7E
--text-inverse:   #0A0A0F
--accent-mint:    #00FFB3
--accent-amber:   #FFB800
--accent-red:     #FF3355
--accent-blue:    #4D9CFF
--grain-opacity:  0.04
--shadow-card:    0 4px 24px rgba(0,0,0,0.4)
--shadow-glow:    0 0 20px rgba(0,255,179,0.2)
```

---

### ☀️ LIGHT THEME TOKENS

```
--bg-base:        #F5F0E8   (warm cream, not white — like aged paper)
--bg-surface:     #FDFAF4   (warm off-white for cards)
--bg-elevated:    #EDE8DC   (slightly darker cream for modals)
--border:         rgba(0,0,0,0.08)
--border-focus:   #008F64   (darker mint for contrast on cream)
--text-primary:   #1A1410   (deep warm black, not pure #000)
--text-muted:     #7A7060
--text-inverse:   #F5F0E8
--accent-mint:    #007A55   (darkened mint — readable on cream)
--accent-amber:   #C47D00   (darkened amber — readable on cream)
--accent-red:     #CC1F3A
--accent-blue:    #1A6FCC
--grain-opacity:  0.025
--shadow-card:    0 2px 16px rgba(0,0,0,0.08)
--shadow-glow:    0 0 16px rgba(0,143,100,0.15)
```

**Light theme character notes:**
- Feels like a premium music magazine — think Pitchfork editorial meets Indian vinyl sleeve design
- Cream background with warm black text creates a human, crafted feel — not clinical
- Mint accent darkens significantly to maintain contrast on cream (never use `#00FFB3` on light bg)
- Grain texture stays — but at half opacity — gives physical texture to digital surfaces
- Track cards: slight warm shadow instead of dark glow

---

## ✍️ TYPOGRAPHY

- **Display/Hero:** `Clash Display` (variable weight 400–700) — sharp, editorial
- **UI Labels, Prices, Data:** `DM Mono` — monospace, grid-aligned
- **Body / Descriptions:** `Satoshi` — clean, warm, not generic
- **Numbers, Prices, Stats:** Always `DM Mono` — critical for alignment across price lists

**Type Scale:**
```
Hero:        Clash Display 80–96px / weight 700 / tight letter-spacing (-0.03em)
Section H2:  Clash Display 40px / weight 600
Card Title:  Satoshi 16px / weight 600
Price:       DM Mono 24–28px / weight 500
Label/Tag:   DM Mono 11px / uppercase / tracking 0.08em
Body:        Satoshi 16px / weight 400 / line-height 1.6
Micro:       Satoshi 12px / muted color
```

---

## 🎞️ MOTION PRINCIPLES

- Page transitions: 280ms ease-out, 6px upward slide + fade
- Button hover: `transform: scale(1.02)`, 150ms — subtle, not bouncy
- Card hover: `translateY(-2px)` + border glow, 200ms ease
- Dangerous actions (delete, freeze, kill switch): brief `shake` keyframe (±4px, 3 cycles) before confirm modal
- Token countdown timer: pulses red with `opacity: 0.7 → 1` at 1s interval when < 60s remain
- Download progress bar: CSS `width` transition chunked to actual server bytes — smooth fill
- Theme toggle: sun/moon icon rotates 180° on switch, 300ms ease
- Skeleton loaders: use `shimmer` gradient animation, not spinner — matches card shape exactly

---

## 🧭 NAVIGATION

### Desktop Nav (sticky, full-width)
- **Left:** MixMint wordmark — Clash Display 22px, accent mint dot after the "t"
- **Center:** `Browse` · `New Releases` · `Top DJs` — Satoshi 15px
- **Right:** Theme toggle (sun/moon) · `Login` · `Sign Up` (mint ghost button)
- If logged in (buyer): replace login/signup with avatar + `My Library` link
- If DJ: avatar + `DJ Panel` link
- Nav background: `--bg-base` at 90% opacity + `backdrop-filter: blur(12px)` — readable without heavy bar
- Bottom border: 1px `--border` — barely visible

### Mobile Nav
- Hamburger top-right → full-screen overlay menu (dark/cream bg)
- Links animate in with stagger (50ms delay each)
- Bottom tab bar for logged-in users: Home · Search · Library · Profile

---

## 🏠 1. PUBLIC HOMEPAGE

### Hero Section
- Full viewport height (100dvh)
- **Headline:** *"Own the Drop."* — Clash Display 96px, `--text-primary`, weight 700
- **Sub-headline:** *"India's only DJ music marketplace where you truly own what you buy."* — Satoshi 20px, `--text-muted`
- **CTAs:** Side by side
  - `Browse Music` — mint filled, 52px, rounded-8 (not rounded-full — intentional sharpness)
  - `Become a DJ Partner` — ghost, mint border 1.5px, same height
- **Background (dark):** Grain texture overlay 4% + three slow-drifting radial color blobs (mint, deep purple, amber) at 0.15x speed, blurred 160px, opacity 6%
- **Background (light):** Same grain at 2.5% + faint warm amber and green blobs, much lower opacity — feels like sunlight through a window
- Decorative: Abstract geometric line art (NOT waveform — just angular diagonal lines suggesting a mixing board or vinyl grooves), SVG, static, positioned bottom-right, 30% opacity

### Trust Bar
- Scrolling marquee strip, `--bg-elevated`, 40px height
- Items in DM Mono 12px, `--text-muted`:
  `🔒 Secure Token Downloads` · `85% Revenue to DJs` · `ZIP Album Packs` · `No Streaming` · `Device-Locked Files` · `India-First Platform` · `No Subscriptions`
- Subtle left/right gradient fade mask on the strip edges

### Featured DJs Row
- Label: `PARTNERED DJs` — DM Mono 11px, `--accent-mint`, uppercase, 0.1em tracking
- Horizontal drag-scroll row (no arrows on desktop, visible on mobile)
- **DJ Card (200×240px):**
  - Top 60%: DJ photo/avatar, full-bleed, `object-fit: cover`
  - Bottom 40%: `--bg-surface` panel, DJ name (Satoshi 15px bold), genre tags (DM Mono pills)
  - Verified badge: small ✦ mint icon top-right corner of photo, with `title="Verified DJ"` tooltip
  - Track count: DM Mono 11px muted, bottom of card
  - Hover: card border shifts to `--accent-mint` at 40% opacity, photo slightly zooms (scale 1.04, overflow hidden)

### New Releases Grid
- Label: `NEW RELEASES`
- 4-col → 2-col → 1-col grid
- **Track Card:**
  - Artwork: square, rounded-10, full-bleed image
  - Genre pill: top-left overlay on image, `--bg-base` 80% opacity, DM Mono 10px
  - If album: `ZIP` badge top-right, amber
  - Below image: Track title (Satoshi 15px 600), DJ name (link, 13px muted), Price (DM Mono 18px `--accent-mint`), Buy button
  - Buy button: full card width, `--accent-amber` text on `--bg-surface` background in light mode — reversed in dark
  - Preview icon (▶ YouTube / 📱 Instagram): small icon next to DJ name, indicates preview type

### How It Works
- Three numbered cards in a row, connected by a dashed horizontal line (desktop only)
- `01 Browse & Preview` · `02 Pay Once, Own Forever` · `03 Secure Download`
- Cards: `--bg-surface`, border `--border`, rounded-12

### Content Responsibility Notice
*(see Section 21 for full disclaimer spec — appears in footer and below track grid)*

### Footer
- 3-column layout
- Left: MixMint wordmark + tagline + `🇮🇳 India-only. Prices in INR.`
- Center: Browse · Become a DJ · Security · Legal & GST · Contact
- Right: *"All music on MixMint is uploaded and sold by independent DJs. MixMint is not responsible for the content, ownership, or licensing of uploaded files."* — Satoshi 12px, muted, italic
- Bottom strip: Copyright · Privacy · Terms · Refund Policy
- Theme toggle also in footer (for discoverability)

---

## 🔍 2. SEARCH & DISCOVERY PAGE

### Search Bar
- Sticky at top, full-width, 64px tall, rounded-8
- Placeholder: *"Search DJs, tracks, genres, years..."*
- Live autocomplete — grouped: `DJs` / `Tracks` / `Albums` / `Genres`
- Each autocomplete row: thumbnail + name + type badge (DM Mono pill)
- Keyboard navigable (↑↓ Enter Escape)

### Filters
- Desktop: left sidebar 240px, sticky
- Mobile: bottom sheet drawer (slides up on "Filter" button tap)
- Filters: Genre pills (multi-select) · Year range slider · Price range slider · Type (Tracks/Albums/Both) · Sort (Popular This Week / New / Price Low–High / Price High–Low / Top DJ)
- Active filters appear as dismissible chips below the search bar
- `Clear All` link appears when any filter is active

### Results
- Same card layout as homepage
- Count label: DM Mono 13px muted — `142 results for "techno"`
- Infinite scroll + skeleton loaders (match card shape, shimmer animation)
- Empty state: Simple illustration (geometric, not cutesy) + *"Nothing found. Try different keywords or browse all."*

---

## 🎵 3. TRACK DETAIL PAGE

### Layout: Two-column desktop (artwork left, info right) / Stacked mobile

**Left Column — Media**
- Large square artwork, rounded-12, `--shadow-card`
- Preview embed below artwork:
  - Label above: `OFFICIAL PREVIEW` or `INSTAGRAM PREVIEW` — DM Mono 10px, muted, uppercase
  - YouTube full iframe OR Instagram Reel embed — no custom player, no audio player
  - If neither provided: faint placeholder with *"No preview available"*

**Right Column — Info & Purchase**
- DJ row: small avatar (32px circle) + DJ name (link to storefront) + verified ✦ badge
- Track title: Clash Display 32px, `--text-primary`
- Genre tag + Year tag — DM Mono pills
- Price: DM Mono 28px `--accent-mint`
  - Sub-label in 12px muted: *"Inclusive of all taxes"* — this is the only price shown. No GST line. No platform fee line. Clean single number.
- `Buy & Download` — full-width, 56px, `--accent-amber` fill, `--text-inverse`
  - Sub-label: *"Secure one-time download. Device-locked."*
- If already owned: `✓ You Own This` — mint badge, download button below
- Re-download note (small, muted): *"Re-download: available after 2 days · 50% of price"*
- Insurance upsell (if eligible, after 24h): small card — *"Download Insurance — protect against file loss"* with toggle

**Responsibility Disclaimer (below CTA, always):**
> *"This track is uploaded and sold by [DJ Name], an independent artist on MixMint. MixMint distributes but does not verify the licensing or ownership of uploaded content."*
- Satoshi 12px, `--text-muted`, italic
- Small info icon with tooltip linking to `/legal#content-policy`

**Security Notice (below disclaimer):**
- 🔒 *"Protected by MixMint Secure Vault — Token-locked, Device-bound, Byte-verified."*
- Link: `How does this work? →` → Security Standards page

**Ad Placement:**
- Rectangle banner, below security notice
- Labeled `ADVERTISEMENT` — DM Mono 10px muted, above the banner
- Static only. No autoplay. No video. No interstitials.

**Track Metadata Strip (very bottom):**
- Uploaded: [date] · Platform: MixMint · Anti-resale terms embedded in file

---

## 💿 4. ALBUM DETAIL PAGE

Same as Track Detail with additions:
- Track listing: numbered list below artwork — DM Mono, each track name + duration if available
- `📦 Download as ZIP Pack` CTA (replaces track download button)
- ZIP size indicator: `~128 MB` — DM Mono, muted
- Price label: same as track — *"Inclusive of all taxes"*, single number
- Responsibility disclaimer: same format, references DJ name
- Note below CTA: *"This album ZIP includes all tracks with MixMint metadata embedded."*

---

## 👤 5. DJ STOREFRONT PAGE

### Header
- Full-width banner image (DJ-uploaded, 1400×400px, `object-fit: cover`)
- Overlaid bottom section: dark gradient (dark mode) / warm gradient (light mode)
- DJ avatar: 120px circle, 3px `--accent-mint` border, positioned overlapping banner + content
- DJ name: Clash Display 40px
- Verified badge + `Verified DJ` label if approved
- Genre tags + *"Member since [year]"*
- `Follow` button — ghost (placeholder, no backend yet)

### Responsibility Banner (below header, always visible)
- Thin strip, `--bg-elevated`, 1px `--border` bottom
- Satoshi 12px, muted, italic:
  > *"All music on this page is independently uploaded by [DJ Name]. MixMint is not responsible for content licensing or ownership."*

### Tabs: `Tracks` / `Albums`
- Track/Album grid — same card layout
- Store paused state: full-page message *"Store is temporarily paused."*

---

## 🔐 6. AUTH PAGES

### Login
- Centered card, 440px, `--bg-surface`, `--shadow-card`, rounded-16
- MixMint logo at top
- Google Sign-In first (most prominent — white/cream button with Google logo)
- `— or continue with email —` divider
- Email + Password fields
- `Log In` CTA
- `Forgot Password` · `Create Account` links below
- Note: *"Temporary email addresses are blocked."* — 12px muted

### Register
- Same card
- Google Sign-Up first
- Email, Password, Confirm Password
- Checkbox (required): *"I agree to MixMint's Terms of Service and Anti-Resale Policy"*
- Checkbox (required): *"I understand that content on MixMint is uploaded by independent DJs, and I will not hold MixMint liable for content disputes."*
- Email verification on submit

### Forgot Password
- Email field only
- Resend timer: DM Mono countdown `Resend in 0:45` — live, no refresh needed

---

## 🛒 7. CHECKOUT FLOW

### Price Display Philosophy (CRITICAL)
**Never show GST and platform fee as separate line items to buyers.**
The user sees one clean price. Taxes and fees are already baked in. The invoice PDF (downloadable after purchase) contains the legal breakdown internally — but the checkout UI shows only the final number.

### Step 1: Order Summary
```
┌─────────────────────────────────────┐
│  [Track Art]  Track Name            │
│               by DJ Name            │
│                                     │
│               Price    ₹49          │
│               ─────────────────     │
│               You Pay  ₹49          │
│                                     │
│  [Proceed to Pay]                   │
│                                     │
│  * Inclusive of all applicable      │
│    taxes and platform charges.      │
│  * A detailed invoice will be       │
│    sent to your email.              │
└─────────────────────────────────────┘
```
- DM Mono for all numbers
- The `You Pay` line = the single clean total
- No `GST (18%)`, no `Platform Fee`, no `Service Charge` line visible
- Small asterisk note below the total — Satoshi 12px muted
- Full GST invoice auto-emailed post-purchase and downloadable in library

### Step 2: Payment
- Razorpay / PhonePe modal (external gateway)

### Step 3: Post-Payment
- **Success:** Large ✓ checkmark (CSS animated, mint), *"Payment confirmed. Preparing secure download..."*, 3s countdown → auto-redirect to download page
- **Failure:** ✗ Red, error message, `Try Again` button

---

## ⬇️ 8. DOWNLOAD PAGE

**Most critical page. Every pixel matters.**

### Container (centered, max-width 560px)
- Track art + title at top (compact — 60px art, title beside it)
- **Token Status bar:**
  - Mint pill: `🔐 Token Active`
  - Countdown: DM Mono, `--accent-mint` → shifts to `--accent-red` when < 60s
  - At < 60s: pulsing red dot appears, warning text: *"Token expiring — download now"*
- **Download Button:**
  - `⬇ Download Now` — 64px tall, full-width, `--accent-mint` fill, dark text
  - On click: button disables, transitions to progress state
- **Progress Bar:**
  - Full width, `--accent-mint` fill, rounded-4
  - DM Mono percentage ticker inside bar: `67%`
  - Speed label below: DM Mono 12px muted — `2.4 MB/s`
  - Animated diagonal stripe pattern while active (CSS only)
- **Attempt Counter:** DM Mono 13px muted — `Attempt 1 of 3`
  - 2 remaining: amber warning strip — *"⚠ 2 attempts remaining for this IP"*
  - 1 remaining: red warning strip — *"🚨 Final attempt. Ensure a stable connection."*
- **Completion State:**
  - Progress bar fills fully, shifts to solid mint
  - ✓ label inside bar: `Complete — Verified`
  - Below: *"Your file has been locked to this device. Check your Library."*
  - `Go to Library →` button
- **Failure State:**
  - Bar fills red
  - *"Download incomplete — file not verified. You are eligible for a refund or retry."*
  - `Request Refund` · `Retry` buttons side-by-side

### Warning Notice (always pinned above button)
> *"Do not close or refresh this tab during download. Incomplete downloads are not counted as successful and do not consume your attempts."*

### Ad Placement
- Static banner ONLY, below the container
- Labeled `ADVERTISEMENT`
- No video. No autoplay. No popups.

---

## 📚 9. USER LIBRARY

### Tabs: `Owned Tracks` / `Owned Albums`

**Per item:**
- Art thumbnail (48px) + Title + DJ name
- Purchase date — DM Mono 12px muted
- Download status badge: `✓ Downloaded` / `⏳ Pending` / `✗ Incomplete`
- Re-download state:
  - Eligible: `Re-download · ₹25` — amber button
  - Locked: DM Mono countdown — *"Available in 1d 4h"* — muted, disabled button
- Insurance badge if active: `🛡 Insured` — mint pill
- Incomplete download: `Request Refund` link — red text, 12px

**GST Invoice link per purchase:**
- Small `Download Invoice` link — DM Mono 11px, muted, beside purchase date

---

## 🎛️ 10. DJ DASHBOARD

### Layout: Left sidebar (240px, fixed) + main content

### Sidebar
- MixMint logo at top
- DJ avatar + name + `DJ Panel` label
- Nav: Overview · My Tracks · My Albums · Earnings · Payouts · Collaborations · Store Settings · Upgrade to Pro
- Bottom of sidebar: `View My Storefront →` link

---

### 10.1 Overview
**4 KPI cards (top row):**
- Lifetime Earnings · This Month · Total Sales · Pending Payout
- DM Mono large numbers, `--accent-mint`
- Subtle directional arrows (up/down) for trend vs last period

**Revenue Chart:**
- 12-week line chart — `--accent-mint` line, `--accent-amber` area fill
- Hover tooltip (DM Mono): exact week amount

**Top 5 Tracks table:**
- Rank · Track · Sales · Revenue — compact, DM Mono numbers

---

### 10.2 My Tracks

**Track List Table:**
- Cover thumbnail · Title · Genre · Price · Sales · Revenue · Status toggle · Actions
- Status: `Active` (mint) / `Paused` (muted gray) — pill toggle
- Actions: `Edit` · `Pause` · `Delete` (soft only — triggers shake animation + confirm modal)

**Upload New Track — Full Form:**

**Price Field (CRITICAL — DJ must understand what buyer pays):**

```
┌─────────────────────────────────────────────────────────┐
│  Your Price (what you receive after 15% commission)     │
│  ┌─────────────────────────────────────────────────┐    │
│  │  ₹  [  49  ]                                    │    │
│  └─────────────────────────────────────────────────┘    │
│  Minimum: ₹19 for tracks · ₹49 for albums               │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  💡 Buyer sees:  ₹49  (inclusive of all taxes)  │    │
│  │                                                  │    │
│  │  Breakdown (for your reference):                │    │
│  │  Your price set:      ₹49.00                    │    │
│  │  MixMint commission (15%):  −₹7.35             │    │
│  │  Your earnings:       ₹41.65                    │    │
│  │                                                  │    │
│  │  ↳ The buyer pays ₹49 (taxes included in        │    │
│  │    displayed price — no surprise charges)       │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

- This info box updates **live as the DJ types** — recalculates instantly
- Info box uses `--bg-elevated` bg, `--accent-mint` left border, Satoshi 13px
- DM Mono for all numbers in the breakdown
- Heading *"Buyer sees:"* is bold, prominent — this is the key message
- Below the box: *"Set your price knowing the buyer sees exactly this amount, with no extra fees added at checkout."*

**Other Upload Fields:**
- Title, Genre (dropdown), Year
- Preview Type toggle: `YouTube Full Video` ↔ `Instagram Reel`
- Preview URL input (label updates based on type)
- File upload dropzone: dashed border, drag-drop, file size + format shown on drop
- Collaborators: `+ Add Collaborator` (search by DJ username, max 3 total)
  - Revenue % input per collaborator
  - Live validation: shows remaining % — e.g. *"Remaining: 30%"*
  - Error if total ≠ 100%
- **Content Responsibility Checkbox (required before publishing):**
  > *"I confirm that I own the rights to this content or have the legal right to sell it. I understand that MixMint is not responsible for copyright disputes arising from my uploads, and that my account may be suspended for violations."*
  - This must be checked on every upload (not just account-level)
- `Save & Submit for Review` / `Save as Draft`
- After submit: toast — *"Track submitted. Admin review typically takes 24–48 hours."*

---

### 10.3 My Albums
- Same structure as Tracks
- ZIP upload with track list input
- Same price info box — live breakdown, same copy
- Same content responsibility checkbox per upload

---

### 10.4 Earnings
- Filters: This Week / This Month / All Time / Custom Date Range
- Summary row: Sales Revenue + Ad Revenue = Total Earnings
- Per-Track Revenue table (DM Mono numbers, right-aligned)
- Per-Album Revenue table
- Collab tracks: show split per collaborator in sub-row

---

### 10.5 Payouts
**Wallet Card:**
- Available: `₹2,450` (DM Mono 32px, `--accent-mint`)
- Escrow Reserve: `₹300` — muted, with tooltip explaining escrow
- Threshold status: `₹500 minimum met ✓` — mint, or `₹320 needed to unlock payout` — amber

**2FA Gate:**
- If 2FA not enabled: full amber banner — *"🔐 Enable 2FA to access payouts. Required for security."* — with `Enable Now` link
- If 2FA enabled: payout history table visible

**Payout History:**
- Date · Amount · Status · Reference
- Status: `Paid` (mint) / `Pending` (amber) / `Failed` (red) / `Held` (gray with tooltip)

---

### 10.6 Store Settings
- Store Status: large toggle — `Active` / `Paused`
  - Pausing shows: *"Your storefront will show a paused message to buyers. Existing purchases are unaffected."*
- Display name, bio, avatar upload (circle preview), banner image upload (strip preview)
- Default preview type preference
- Pro Plan upgrade card (if not Pro): outlines benefits — lower commission, custom domain, reduced ads

---

## 👑 11. ADMIN DASHBOARD

### Sidebar
- `⚡ ADMIN` badge in red pill beside logo
- Nav: Platform Overview · DJ Applications · Content Moderation · Revenue Intelligence · Payout Management · Security & Risk · Platform Controls · Investor Report

---

### 11.1 Platform Overview
**6 KPI cards:**
- Platform Revenue (lifetime) · Commission (this month) · Ad Revenue (this month) · Active DJs · Monthly Purchases · Pending Payouts

**Revenue Donut Chart:** Commission vs Ad Revenue vs Service Fees

**High-Value Alerts:** Red card if flagged — User · Amount · Flag Reason · Investigate / Clear

---

### 11.2 DJ Applications
- Table: Applicant · Email · Applied Date · Fee Status · Status · Actions
- Status: `Pending` (amber) / `Approved` (mint) / `Rejected` (red)
- Actions: Approve · Reject · Grant Verified Badge

**Application Fee Control (top of page):**
```
┌─────────────────────────────────────────────────────────┐
│  DJ Application Fee                                     │
│                                                         │
│  [  OFF  ●──────────────  ] Currently: DISABLED        │
│                                                         │
│  When enabled, new DJs pay ₹99 to apply.               │
│  Currently running introductory FREE period.            │
│  Enable this when the promo period ends.                │
│                                                         │
│  Fee Amount: [₹ 99 ]  (editable when enabled)          │
└─────────────────────────────────────────────────────────┘
```
- Toggle is OFF by default (introductory offer period)
- Toggle turns amber when enabled, with confirmation modal: *"Enabling this will require all new DJ applicants to pay ₹99. Existing DJs are unaffected. Confirm?"*
- Fee amount field is grayed out when toggle is OFF

---

### 11.3 Content Moderation
- Table: Content · DJ · Type · Uploaded · Reports · Status · Actions
- Actions: Review · Soft Delete · Restore
- On delete: modal — *"DJ will be notified via email. Content will be archived, not permanently deleted."* — requires confirm
- **Moderation Responsibility Note (top of page):**
  > *"Content on MixMint is uploaded by independent DJs. DJs are contractually responsible for their uploads. Moderation here enforces platform policy — it does not imply MixMint ownership or endorsement of content."*

---

### 11.4 Revenue Intelligence
- 12-month commission vs ad revenue line chart
- Top 10 DJs by platform revenue generated
- **Ad Floor Pricing Control:** `Floor Price: ₹ [X] CPM` input + Save
- Investor Report: Monthly / Quarterly / Annual toggle + Export PDF

---

### 11.5 Payout Management
- Full payout table with filters
- `Process Weekly Payouts` — amber button, confirm modal
- Per-payout: Hold (reason input) · Release · Mark Paid
- **Global Freeze Payout:** emergency amber toggle — freezes all outgoing payouts

---

### 11.6 Security & Risk
**IP & Device Blacklist:**
- Table: IP/Device · Reason · Blocked Date · Unblock
- `+ Add to Blacklist` form

**Suspicious Activity Log:**
- User · Action · IP · Device · Flag · Timestamp
- Actions: Freeze Account · Clear Flag

**Emergency Controls:**
- **Kill Switch** (Downloads Disabled): giant red toggle
  - Requires typing `CONFIRM` in input field before activating
  - Shows: *"Last activated: Never"* or timestamp
- **Maintenance Mode:** amber toggle, live status shown

---

### 11.7 Platform Controls
- Application fee toggle + amount (same as 11.2, synced)
- Temp email blocklist: add/remove domains
- Session timeout duration
- Password strength enforcement settings
- **Platform Fee for Buyers:** toggle (currently disabled — introductory offer)
  ```
  Buyer Platform Fee:  [  OFF  ●──]  Currently: DISABLED
  
  When enabled, a small service fee is added to buyer checkout.
  Currently disabled as introductory offer. Enable via admin decision.
  Amount: [₹ 5 ]
  ```
  - Same pattern as DJ fee — OFF by default, admin-controlled

---

## 📱 12. MOBILE RESPONSIVENESS

### Bottom Tab Bar (logged in):
- Home · Search · Library · Profile
- DJ Panel: Profile → `My DJ Panel` link

### Mobile behaviors:
- All cards: single column, full-width
- Download button: 72px tall, touch-optimized
- Filter: bottom sheet (slides up, 60% screen height, scrollable)
- Album artwork: full-width crop
- DJ Dashboard: sidebar collapses to hamburger top-left
- Price info box on upload: collapsible by default — *"Show buyer price breakdown ▾"* — taps to expand

### Touch details:
- All tap targets: minimum 48×48px
- DJ storefront tab switcher: swipe left/right
- Library: pull-to-refresh
- Download complete: `navigator.vibrate(200)` — single haptic pulse

---

## ♿ 13. ACCESSIBILITY (WCAG 2.1 AA)

- Keyboard-navigable: all interactive elements reachable via Tab
- Focus rings: 2px `--border-focus` outline, 2px offset
- ARIA labels on all icon-only buttons
- Contrast: all text ≥ 4.5:1 — both themes verified separately
- Screen reader: proper H1→H6 hierarchy per page
- Skip to main content: visually hidden, focus-visible
- Error messages: linked to fields via `aria-describedby`
- Progress bar: `role="progressbar"` + `aria-valuenow` + `aria-valuemax`
- Theme toggle: `aria-label="Switch to light mode"` / `"Switch to dark mode"` — updates dynamically
- Disclaimer text: not hidden behind tooltips on mobile — always visible

---

## 🔔 14. NOTIFICATIONS & TOASTS

**Toast (top-right, 360px wide, rounded-10):**
- ✓ Success: `--accent-mint` left border — *"Track uploaded successfully"*
- ⚠ Warning: `--accent-amber` — *"1 download attempt remaining"*
- ✗ Error: `--accent-red` — *"Token expired. Refresh to try again."*
- ℹ Info: `--accent-blue` — *"Your payout is being processed"*
- Auto-dismiss: 5s with progress bar at bottom of toast
- Max 3 stacked; oldest dismisses when 4th appears
- Close button (×) on each

**Emails via Resend:**
- Purchase confirmation + GST invoice PDF attached
- Download attempt warning (1 remaining)
- Successful download confirmation
- Payout processed
- DJ content moderated (with reason)
- Weekly DJ earnings summary
- DJ application approved/rejected

---

## 🔒 15. SECURITY STANDARDS PAGE (`/security`)

Public page — human-readable, not a wall of tech jargon.

Sections:
- **Token System** — how one-time tokens work, why they expire
- **Device Binding** — what device-locking means for buyers
- **Private File Storage** — no public URLs, all via Cloudflare R2 private
- **Attempt Limits** — 3 per IP, what happens on failure
- **Byte Verification** — what counts as a successful download

Footer of this page:
> *"MixMint's security systems protect file delivery. Content licensing responsibility lies with the uploading DJ, not MixMint. See our Content Policy for details."*

---

## 📄 16. GST INVOICE (Email + Download)

- Auto-generated on every purchase
- **Buyer-facing invoice** (email + library download):
  - Shows: Buyer name, DJ name, Track/Album title, total paid, GST breakdown (internal), invoice number, date
  - Clean, minimal PDF — not a legal-heavy wall of text
- **DJ GST Export:**
  - Available in Earnings section
  - Download CSV or PDF — all invoices, with GST breakdown per sale
  - For DJ's own GST filing use

---

## 🎨 17. COMPONENT LIBRARY

### Buttons
```
Primary (dark):   bg #00FFB3, text #0A0A0F, rounded-8, h-44px, Satoshi 15px 600
Primary (light):  bg #007A55, text #FDFAF4, rounded-8, h-44px
Secondary:        bg --accent-amber variant, same shape
Ghost:            transparent, 1.5px --accent-mint border, --accent-mint text
Danger:           bg --accent-red, white text
Disabled:         bg --bg-elevated, --text-muted text, cursor-not-allowed, no hover
```

### Inputs
```
bg: --bg-surface
border: 1px solid --border
border (focus): 1.5px --border-focus
border (error): 1.5px --accent-red
text: --text-primary
placeholder: --text-muted
height: 48px, padding: 12px 16px, rounded: 8px
```

### Status Pills
```
Success: --accent-mint at 15% opacity bg, --accent-mint text
Warning: --accent-amber at 15% opacity bg, --accent-amber text
Error:   --accent-red at 15% opacity bg, --accent-red text
Neutral: --border bg, --text-muted text
```

### Cards
```
bg: --bg-surface
border: 1px solid --border
border-radius: 16px
padding: 20px
hover: border-color at 40% --accent-mint, translateY(-2px)
transition: all 0.2s ease
shadow: --shadow-card
```

### Info/Notice Boxes
```
bg: --bg-elevated
left border: 3px solid --accent-mint (info) / --accent-amber (warning) / --accent-red (danger)
border-radius: 8px
padding: 14px 16px
text: Satoshi 13px --text-primary
```

---

## 📐 18. SPACING & LAYOUT

- Base unit: 4px
- Page max-width: 1280px, centered
- Horizontal padding: 20px (mobile) / 48px (tablet) / 80px (desktop)
- Section gap: 80px desktop / 48px mobile
- Grid: 12-col, 24px gutter
- Card gap: 16px compact / 24px standard

---

## 🚫 19. WHAT NEVER APPEARS

- ❌ No audio player, waveform, or any streaming interface
- ❌ No subscription plans for buyers
- ❌ No referral or affiliate program UI
- ❌ No gamification, points, badges, streaks
- ❌ No social feed, comments, or likes
- ❌ No publicly visible download counts
- ❌ No demographic analytics in DJ dashboard
- ❌ No autoplay ads, video ads, or popups
- ❌ No download links in the UI (all through secure proxy only)
- ❌ No direct R2 URLs ever exposed
- ❌ No "Platform Fee" or "GST" labels in buyer-facing checkout UI
- ❌ No platform fee charged at checkout (disabled by default, admin-controlled)
- ❌ No DJ application fee charged (disabled by default, admin-controlled)

---

## 💬 20. CRITICAL UX COPY REFERENCE

**Checkout price note:**
> *"Inclusive of all applicable taxes and platform charges."*

**Download page pin notice:**
> *"Do not close or refresh this tab. Incomplete downloads are not marked successful and will not consume your attempts."*

**Token expiry warning:**
> *"Token expiring — download now."*

**Final attempt warning:**
> *"🚨 Final attempt. Ensure a stable connection before proceeding."*

**Download complete:**
> *"File verified and locked to this device. Check your Library."*

**Download failed:**
> *"Download incomplete. You are eligible for a refund or a retry."*

**Re-download note:**
> *"Re-download: available 2 days after completion · 50% of original price"*

**Store paused:**
> *"This DJ has temporarily paused their store."*

**Security badge:**
> *"Protected by MixMint Secure Vault — Token-locked · Device-bound · Byte-verified"*

---

## ⚖️ 21. CONTENT RESPONSIBILITY — WHERE & HOW IT APPEARS

MixMint is a marketplace. DJs are responsible for what they upload. This must be communicated clearly, consistently, and without being aggressive or accusatory.

### Locations & Exact Copy

**Public Homepage Footer:**
> *"All music on MixMint is independently uploaded and sold by DJs. MixMint is not responsible for the content, licensing, or copyright of uploaded files."*
Satoshi 12px, --text-muted, italic

**Track Detail Page (below CTA, always):**
> *"This track is uploaded and sold by [DJ Name], an independent artist. MixMint distributes but does not verify the licensing or copyright of uploaded content."*
Satoshi 12px, --text-muted, italic. Link: `Content Policy →`

**Album Detail Page:** Same as track, references "this album."

**DJ Storefront Page (below header banner):**
> *"All music on this page is independently uploaded by [DJ Name]. MixMint is not responsible for content licensing or ownership."*
Thin strip, subtle background, muted italic text

**DJ Upload Form (required checkbox, every upload):**
> *"I confirm that I own or have the legal rights to sell this content. I understand MixMint is not responsible for copyright disputes arising from my uploads, and that violations may result in account suspension or termination."*
Must be checked before submitting. Not pre-checked. Satoshi 13px.

**Admin Content Moderation Page (top notice):**
> *"Content is uploaded by independent DJs under contractual responsibility. Moderation enforces platform policy — it does not imply MixMint ownership or endorsement of any content."*

**Security Standards Page (footer section):**
> *"MixMint's security systems govern file delivery. Content licensing responsibility lies entirely with the uploading DJ. See our Content Policy for details."*

**Register Page (checkbox, required):**
> *"I understand that content on MixMint is uploaded by independent DJs, and I will not hold MixMint liable for content or licensing disputes."*

**Legal/Terms Page:** Full section on content responsibility, DMCA process, what buyers and DJs can report, and how disputes are handled.

---

*End of MixMint UI/UX Master Prompt — Version 2.0*
*Updated: Dual theme system · Unified buyer pricing · DJ price transparency · Content responsibility layer · Platform fee admin control*
*For mixmint.site — India's DJ-first secure music marketplace*
