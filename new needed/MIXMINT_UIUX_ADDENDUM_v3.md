# 🎛️ MIXMINT — ADDENDUM PROMPT (v2 → v3 CHANGES ONLY)
### *Apply these changes on top of the existing v2 implementation*

---

## 🎁 CHANGE 1 — OCCASION-BASED OFFER SYSTEM (Admin-Controlled)

### Concept
MixMint runs time-limited promotional offers tied to occasions — launch week, festivals, milestones, etc. These are fully controlled by admin. No hardcoded offers anywhere in the frontend. Everything is fetched from the backend.

**Current active example (Launch Offer):**
- Platform commission: 10% (standard is 15%)
- Platform fee for buyers: ₹0 (waived)
- GST: Not charged (below ₹10L turnover threshold — do not mention GST at all in UI until admin enables it)
- This is just the launch config — admin can change all of this at any time

---

### Admin Dashboard — Offer Management (New Section)

Add a new sidebar item in Admin: **🎁 Offers & Pricing**

#### Page Layout:

**Section 1 — Live Pricing Control**
```
┌──────────────────────────────────────────────────────────┐
│  PLATFORM COMMISSION RATE                                │
│  Current: [ 10 ]%   [Save]                              │
│  This is deducted from every DJ sale before payout.     │
│  Applies to all new purchases immediately on save.      │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  BUYER PLATFORM FEE                                      │
│  [  OFF  ●───────  ]  Currently: WAIVED (₹0)           │
│  Amount when enabled: [ ₹5 ]                            │
│  When enabled, added into the buyer's total silently.   │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  GST CHARGING                                            │
│  [  OFF  ●───────  ]  Currently: NOT CHARGING           │
│  Enable when platform turnover crosses ₹10L threshold.  │
│  When enabled, GST is calculated and included in the    │
│  buyer's total silently. Never shown as a line item.    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  DJ APPLICATION FEE                                      │
│  [  OFF  ●───────  ]  Currently: FREE                   │
│  Amount when enabled: [ ₹99 ]                           │
└──────────────────────────────────────────────────────────┘
```
- All fields: live save with confirmation toast
- All toggles: confirmation modal before switching ON
- Changes take effect immediately platform-wide

---

**Section 2 — Active Offer Banner**

```
┌──────────────────────────────────────────────────────────┐
│  PROMOTIONAL OFFER BANNER                                │
│                                                          │
│  [ ON  ●─────────  ]  Banner currently: ACTIVE         │
│                                                          │
│  Offer Title:     [ Launch Offer 🚀              ]      │
│  Offer Tagline:   [ Zero platform fees. 10% comm ]      │
│  Offer Sub-text:  [ Introductory launch pricing  ]      │
│  Badge Label:     [ LIMITED TIME                 ]      │
│  Occasion Tag:    [ Launch / Festive / Custom    ] ▾    │
│                                                          │
│  Start Date:  [ DD/MM/YYYY ]                            │
│  End Date:    [ DD/MM/YYYY ] or [ No end date ✓ ]       │
│                                                          │
│  Show on:                                               │
│  [✓] Homepage hero                                      │
│  [✓] Navbar announcement strip                          │
│  [✓] DJ upload page                                     │
│  [✓] Checkout page                                      │
│  [ ] Track/Album pages                                  │
│                                                          │
│  [Preview Banner]  [Save & Publish]                     │
└──────────────────────────────────────────────────────────┘
```

- Offer content is fully CMS-like — admin types whatever the offer is
- No hardcoded offer text anywhere in frontend
- If banner is OFF: nothing shows site-wide (clean UI)
- Multiple offers can be queued (future), but only one active at a time currently

---

## 🎬 CHANGE 2 — OFFER BANNER ANIMATION (Visitor-Facing)

### Where It Appears
Every page load for every visitor (logged in or not), if admin has an active offer banner enabled.

---

### Navbar Announcement Strip

- Fixed strip **above** the main navbar, full-width
- Height: 36px
- Background (dark): deep mint-tinted dark — `#0D1F18`
- Background (light): warm amber-tinted cream — `#FDF3DC`
- Text: DM Mono 12px, centered
- Content: scrolling marquee of offer text — left to right, smooth loop
- Example text: `🚀 LAUNCH OFFER — Zero platform fees · 10% commission for DJs · Limited time only · 🚀 LAUNCH OFFER — Zero platform fees · 10% commission for DJs`
- Right side: `×` close button — dismisses for session (stored in sessionStorage, not localStorage — reappears on new session/visit)
- **Pulse animation:** The strip has a very subtle `opacity: 0.85 → 1` pulse at 3s interval — draws the eye without being obnoxious

---

### Homepage Hero — Offer Card (Floating Entry Animation)

When visitor lands on homepage and an offer is active, a floating offer card animates in:

**Animation sequence:**
1. Page loads normally (hero visible)
2. After 1.2s delay — offer card slides in from bottom-right corner
3. Entry: `translateY(80px) → translateY(0)` + `opacity: 0 → 1`, 400ms cubic-bezier(0.16, 1, 0.3, 1) — smooth spring feel
4. Card stays visible — does not auto-dismiss
5. User can close it (×) — session-dismissed

**Card design (dark mode):**
```
┌─────────────────────────────────────┐  ← rounded-16, shadow-heavy
│  🚀  LIMITED TIME OFFER       [×]  │  ← DM Mono badge (amber), close icon
│                                     │
│  Launch Offer                       │  ← Clash Display 22px, white
│  Zero platform fees                 │  ← Satoshi 14px muted
│  10% commission for DJs             │  ← Satoshi 14px muted
│                                     │
│  ══════════════════════  animated  │  ← thin mint shimmer line, left→right
│                                     │
│  [  Learn More  ]                   │  ← ghost button → /offers or modal
└─────────────────────────────────────┘
```

**Card design (light mode):**
- Background: `#FDFAF4` warm white card
- Border: 1.5px `--accent-amber` (light)
- Title: deep warm black
- Badge: amber filled pill
- Shimmer line: warm green

**Shimmer line animation:**
- A 2px horizontal line inside the card
- Animates a bright highlight traveling left to right, looping every 2.5s
- CSS keyframes: `background-position: -200% → 200%` on a gradient
- Subtle — not a loud loading bar

---

### Checkout Page — Offer Reminder

If an active offer exists, show a small inline notice above the price total:

```
┌──────────────────────────────────────────────┐
│  🎁  Launch Offer active — zero platform     │
│       fees applied to this purchase.         │
└──────────────────────────────────────────────┘
```
- `--bg-elevated` background, `--accent-mint` left border 3px
- Satoshi 13px
- This reinforces to the buyer they're getting a good deal — not that fees were hidden

---

### DJ Upload Page — Offer Awareness Strip

Above the price info box on upload, if commission rate is non-standard:

```
┌──────────────────────────────────────────────┐
│  🚀  Launch Offer: Commission is 10% now     │
│       (standard rate is 15%)                 │
└──────────────────────────────────────────────┘
```
- Amber left border info box
- Updates live from backend — shows whatever the current commission rate is

---

## 💰 CHANGE 3 — UNIFIED PRICING ENGINE (Frontend Rules)

### The Golden Rule
**Buyers always see one number. One price. Nothing else.**

All charges — commission impact, platform fee, GST (when enabled) — are calculated server-side and folded into the single display price. The frontend never adds, labels, or shows individual charge components to buyers anywhere.

### Implementation Rules

**Track/Album pages:**
- Price shown: single number from backend — `₹49`
- Sub-label: *"Inclusive of all charges"* — Satoshi 11px muted
- Nothing else

**Checkout:**
```
Track Name                     ₹49
─────────────────────────────────
You Pay                        ₹49

* Inclusive of all charges.
  Invoice sent to your email.
```
- No line-by-line breakdown
- No GST row
- No fee row
- Just the total

**Post-purchase invoice (email PDF only):**
- This is where the legal breakdown lives
- Shows: base price, platform charges, applicable tax (if GST enabled)
- Buyers who need it for accounting can access via Library → Download Invoice
- Never shown in the UI flow itself

**When GST is OFF (current):**
- No mention of GST anywhere in UI — not even "GST not applicable"
- Silence is correct — don't draw attention to it

**When GST is ON (admin enables later):**
- Still not shown as a line item in checkout
- Only appears in the invoice PDF
- UI copy changes from *"Inclusive of all charges"* to nothing different — same clean display

---

### DJ Price Info Box — Updated for Dynamic Commission

The live breakdown box on upload updates to reflect whatever commission rate is currently set by admin:

```
┌─────────────────────────────────────────────────────────┐
│  💡 Buyer sees:  ₹49  (inclusive of all charges)        │
│                                                          │
│  Your earnings breakdown:                               │
│  Price set by you:          ₹49.00                      │
│  Platform commission (10%): −₹4.90   ← dynamic %       │
│  Your earnings:             ₹44.10                      │
│                                                          │
│  The buyer pays exactly ₹49. No extra fees added.       │
└─────────────────────────────────────────────────────────┘
```
- Commission % shown in the breakdown is pulled from backend config
- If a promo offer is active: small amber badge beside the % — `LAUNCH OFFER`
- Breakdown is for DJ's reference only — never shown to buyers

---

## 🔓 CHANGE 4 — BROWSE-FIRST AUTH FLOW

### New Rule: Browse Without Login

Users can do the following **without any account:**
- Browse homepage
- View search results
- Open any track or album detail page
- See price and all track info
- Watch the YouTube/Instagram preview embed
- Read DJ storefront page

Users are **only prompted to log in when they attempt to:**
- Click `Buy & Download` on any track/album → redirect to login, then return to same page after login
- Apply to become a DJ

**Never:**
- No login wall on browse pages
- No "Sign in to view" on track pages
- No forced registration prompts on scroll or time-based popups

---

### Buy Flow — Unauthenticated User

1. User on track page, not logged in
2. Clicks `Buy & Download`
3. Smooth modal slides up (not a page redirect):
   ```
   ┌─────────────────────────────────┐
   │  Log in to purchase             │
   │                                 │
   │  [Continue with Google]         │
   │         — or —                  │
   │  [Email]  [Password]            │
   │  [Log In]                       │
   │                                 │
   │  No account? Create one →       │
   └─────────────────────────────────┘
   ```
4. After successful login: modal closes, checkout flow begins automatically for the same track
5. No page reload. No lost context.

**If user creates account instead:**
- After email verification: auto-redirected back to the same track page
- Track page shows purchase button active, ready to buy

---

### DJ Application — Role Upgrade Flow

**"Become a DJ" is a role upgrade, not a separate registration.**

Any logged-in user with role `user` can apply to become a DJ.

**Entry points for "Become a DJ":**
- Navbar link (always visible to logged-in users without DJ role)
- Homepage hero secondary CTA
- User profile page → `Apply as DJ Partner`

**Application Flow:**

**Step 1 — Not logged in:**
- Clicking "Become a DJ" → same auth modal as above
- After login → automatically continues to DJ application form

**Step 2 — Application Form (logged-in user):**
```
┌──────────────────────────────────────────────────────┐
│  Apply to Become a DJ Partner                        │
│                                                      │
│  DJ Display Name      [                    ]         │
│  Genre(s)             [multi-select pills  ]         │
│  Short Bio            [textarea, 200 chars ]         │
│  Social/Music Link    [SoundCloud, YouTube, etc.]    │
│  Why MixMint?         [textarea, 300 chars ]         │
│                                                      │
│  If DJ application fee is enabled (admin-set):       │
│  ┌────────────────────────────────────────────────┐  │
│  │  Application Fee: ₹99                          │  │
│  │  [Pay & Submit Application]                    │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  If fee is disabled (current — FREE period):         │
│  [Submit Application]  ← no payment step             │
│                                                      │
│  [✓] I agree that I am responsible for all content  │
│      I upload. MixMint is not liable for disputes   │
│      arising from my uploads.                        │
└──────────────────────────────────────────────────────┘
```

**Step 3 — Submitted state:**
- Page shows: *"Application submitted. Admin review typically takes 24–48 hours. You'll be notified by email."*
- User account remains role `user` until admin approves
- User can still browse and purchase as normal while pending

**Step 4 — Admin approves:**
- Admin clicks `Approve` in DJ Applications table
- System changes user role from `user` → `dj` in `profiles` table
- Email sent to user: *"Congratulations — your DJ application has been approved. Log in to access your DJ Panel."*
- On next login: user sees `DJ Panel` in navbar, full dashboard unlocked

**Step 5 — Admin rejects:**
- Email sent: *"Your DJ application was not approved at this time."* (with optional reason if admin typed one)
- User remains as normal buyer — can reapply (admin-controlled cooldown)

---

### Navigation State Logic (4 states)

**State A — Logged out:**
- Navbar: `Browse` · `New Releases` · `Top DJs` · `Login` · `Sign Up`
- All browse pages accessible
- Buy/Download → auth modal

**State B — Logged in as Buyer (role: user):**
- Navbar: `Browse` · `New Releases` · `Top DJs` · `My Library` · avatar menu
- Avatar menu: My Library · My Account · Become a DJ · Logout
- Buy/Download → checkout directly

**State C — Logged in, DJ application pending:**
- Same as State B
- Avatar menu shows: `DJ Application Pending` — non-clickable status pill (amber)

**State D — Logged in as DJ (role: dj):**
- Navbar: `Browse` · `DJ Panel` · `My Library` · avatar menu
- Avatar menu: DJ Panel · My Library · My Storefront · My Account · Logout
- Full DJ dashboard accessible

---

## 📐 CHANGE 5 — UPDATED COPY REFERENCE (Additions Only)

**Announcement strip (offer active):**
> *"[Offer Title] — [Offer Tagline] · Limited time only"*
(Pulled from admin config — not hardcoded)

**Offer card on homepage:**
> Title from admin. Tagline from admin. `Learn More` → `/offers` or modal.

**Checkout offer notice:**
> *"[Offer Title] active — [brief tagline] applied to this purchase."*

**DJ upload offer notice:**
> *"[Offer Title]: Commission is [X]% for this period."*

**Track page price sub-label:**
> *"Inclusive of all charges"*

**Checkout total sub-label:**
> *"Inclusive of all charges. Invoice sent to your email."*

**Browse CTA for unauthenticated user (track page):**
> Button: `Buy & Download`
> No lock icon. No "Login to buy." Just the normal button — auth modal triggers on click.

**DJ application pending notice:**
> *"Application submitted. You'll hear from us within 24–48 hours."*

**DJ approved email:**
> *"Your DJ application has been approved. Log in to access your DJ Panel and start uploading."*

---

*End of MixMint Addendum — v2 → v3*
*Changes: Occasion-based offer system · Admin pricing control · Animated offer banner · Unified buyer pricing · Browse-without-login · Role-upgrade DJ application flow*
