# MixMint brand kit

Finished files live in `static/brand/` and are served at `https://mixmint.site/static/brand/<file>`.
DJs see the posts on the Asset pack page (`/tracks/asset-pack/`).

## Brand basics

| | |
|---|---|
| Name | MixMint (one word, capital M twice) |
| Line | Home of DJ Releases. |
| Mint | `#00FFB3` on dark, `#007A55` on light |
| Ink | `#0A0A0F` |
| Cream | `#F5F0E8` |
| Headings | Clash Display 700 (fontshare.com, free for commercial use) |
| Body | Satoshi 500 (fontshare.com) |
| Logo | `static/logo/MIXMINT_WHITE.png` on dark, `MIXMINT_BLACK.png` on light. Keep clear space of half the logo height. |

Voice: short, confident and friendly. Talk to DJs as peers. Say "DJs keep 80%" and "weekly payouts", not jargon.
Never promise numbers you can't show.

## Files

| File | Size | Use |
|---|---|---|
| og-default.png | 1200×630 | Link previews (wired into every page without its own image) |
| profile-mint.png / profile-dark.jpg | 1080×1080 | Instagram, YouTube, X, Facebook profile picture |
| telegram-avatar.png | 640×640 | Telegram bot and channel picture |
| youtube-banner.jpg | 2560×1440 | YouTube channel art (text sits in the safe 1546×423 middle) |
| x-header.jpg | 1500×500 | X header |
| linkedin-banner.jpg | 1584×396 | LinkedIn page |
| post-launch / post-djs / post-samples / post-how .jpg | 1080×1350 | Instagram and Facebook feed |
| story-launch / story-djs .jpg | 1080×1920 | Stories and WhatsApp status |
| reel-cover.jpg | 1080×1920 | Reel / Shorts cover (edit the line under NEW DROP) |
| flyer-a4.jpg | 1240×1754 | Print or WhatsApp flyer for DJ recruitment |

## Changing or adding a design

All designs are HTML in `gen.js`, so text changes take one edit:

```
cd tools/brand
npm i playwright            # once
# put ClashDisplay-700.woff2, Satoshi-500.woff2 (from fontshare.com) and
# logo-white.png, logo-black.png (cropped from static/logo) into tools/brand/fonts/
node gen.js                 # all files into tools/brand/out/
node gen.js post-djs        # just one
```

Copy the new files from `out/` into `static/brand/` (JPG for photos, PNG for the logo and link preview).

## Captions (copy, then edit)

**Launch post**
MixMint is live 🎧 India's home for DJ releases: private edits, remixes, album packs and sample packs, straight from the DJs who made them. Preview, pay with UPI, download in seconds.
👉 mixmint.site
#DJ #DJEdits #Remix #IndianDJ #TuluDJ #KannadaDJ #Bollywood #SamplePack #MixMint

**For DJs**
Your edits deserve a price tag. Open your MixMint store in 2 minutes, keep 80% of every sale and get paid to UPI every week. No follower count needed.
Apply: mixmint.site/sell

**Sample packs**
New on MixMint: sample packs and DJ tool kits. Loops, one-shots, acapellas, intros and FX made by Indian DJs.
mixmint.site/releases?type=samples

**New release (Telegram channel posts these by itself)**
🔥 New on MixMint: {title} by {DJ} · ₹{price}. Preview and buy: {link}
