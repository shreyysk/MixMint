# DJ uploads with Cloudflare R2 (one-time setup)

DJs upload straight from their browser to R2, so files of any size work on Vercel.
The browser needs permission to do that — this is the **CORS policy** on each bucket.

## 1. CORS on both buckets

Cloudflare dashboard → **R2** → open your private bucket (the one in `R2_PRIVATE_BUCKET`, e.g. `mixmint-raw`)
→ **Settings** → **CORS Policy** → **Add CORS policy** → paste → **Save**.
Do the same for the public bucket (`R2_PUBLIC_BUCKET`, e.g. `mixmint-public`).

```json
[
  {
    "AllowedOrigins": ["https://mixmint.site", "https://www.mixmint.site", "https://mix-mint.vercel.app"],
    "AllowedMethods": ["PUT", "GET", "HEAD"],
    "AllowedHeaders": ["Content-Type"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

## 2. Public URL for cover art

Public bucket → **Settings** → **Public access** → turn on the **r2.dev subdomain** (or connect a custom domain
like `cdn.mixmint.site`). Copy the URL (e.g. `https://pub-xxxx.r2.dev`) into the Vercel variable `R2_PUBLIC_URL`
and redeploy. Without it, uploads still work but DJs can't add cover art.

## 3. API token

The R2 API token behind `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` needs **Object Read & Write** on both buckets.

## Test

Log in as an approved DJ → Upload music → pick an MP3 → Publish. If it says
"Upload was blocked", the CORS policy is missing or the site address isn't in `AllowedOrigins`.
