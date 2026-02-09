# MixMint QA Audit Report

## Executive Summary
A comprehensive security and functionality audit of the MixMint platform has revealed **Critical** vulnerabilities in the "Core IP" download system, specifically regarding token security, quota enforcement, and IP locking. While the authentication layer is standard, the business logic for downloads and content management allows for exploitation that could lead to unlimited free downloads and potential storage of malicious content.

---

## 1. Download Security (CORE IP) - 🚨 CRITICAL

### 1.1. Download Token Race Condition (Replay Attack)
*   **Severity:** **Critical**
*   **Location:** `src/app/api/download/route.ts`
*   **Reproduction:**
    1.  Legitimately generate a single download token.
    2.  Use a script (e.g., `curl` or Python) to send 10-50 simultaneous GET requests to `/api/download?token=...` with the same token.
    3.  **Expected:** Only the first request succeeds; others return 403/409.
    4.  **Actual:** Multiple requests succeed because the `is_used` flag is updated *after* the stream is initialized (`r2.send`).
*   **Impact:** A single purchase or subscription quota credit can be used to download the file multiple times or share the link simultaneously with others before it burns.
*   **Fix:** Use an atomic database update to check-and-set the flag.
    ```sql
    UPDATE download_tokens SET is_used = true WHERE token = '...' AND is_used = false RETURNING id;
    ```
    If no row is returned, deny the download.

### 1.2. Missing IP Locking
*   **Severity:** **High**
*   **Location:** `src/app/api/download-token/route.ts` & `src/app/api/download/route.ts`
*   **Reproduction:**
    1.  Generate a download token from IP A.
    2.  Send the token URL to a user on IP B.
    3.  **Expected:** Download fails with "IP mismatch".
    4.  **Actual:** Download succeeds.
*   **Root Cause:** `src/app/api/download-token/route.ts` **does not capture** the user's IP address when inserting the token. Consequently, `src/app/api/download/route.ts` checks `if (tokenRow.ip_address && ...)` which evaluates to false (skip check) when `ip_address` is null.
*   **Fix:** Capture `getClientIp(req)` in the token generation route and insert it into the `download_tokens` table.

### 1.3. Quota Bypass via Bulk Token Generation
*   **Severity:** **High**
*   **Location:** `src/app/api/download-token/route.ts` & `src/app/api/download/route.ts`
*   **Reproduction:**
    1.  User has a subscription with 5 tracks/month quota (0 used).
    2.  User writes a script to request download tokens for 50 different tracks.
    3.  **Expected:** API denies token generation after the 5th token.
    4.  **Actual:** All 50 tokens are generated because quota is only checked against `tracks_used` (DB value), which hasn't incremented yet.
    5.  User downloads all 50 files. The system increments `tracks_used` to 50/5.
*   **Impact:** Massive abuse of subscription limits.
*   **Fix:**
    *   **Option A (Strict):** Increment quota *at token generation time* (reservation model).
    *   **Option B (Check-at-Download):** In `download/route.ts`, re-verify `tracks_used < quota` *before* fulfilling the download.

---

## 2. Content Management & Uploads

### 2.1. MIME Type & Extension Spoofing
*   **Severity:** **Medium**
*   **Location:** `src/app/api/dj/upload/route.ts`
*   **Reproduction:**
    1.  Rename `malicious.exe` to `song.mp3`.
    2.  Upload with `Content-Type: audio/mpeg`.
    3.  **Actual:** Server accepts the file because it trusts client-provided headers and extension.
*   **Fix:** Use a library like `file-type` to inspect the "magic bytes" of the file buffer to verify the actual content type matches the extension.

### 2.2. Missing Virus Scanning
*   **Severity:** **Medium**
*   **Impact:** Platform could host malware distributed to fans.
*   **Fix:** Integrate a scanning service (e.g., ClamAV or a cloud function trigger) before marking the file as public/downloadable.

---

## 3. Subscription System

### 3.1. Fan Upload Quota Separation
*   **Observation:** The code correctly checks `fan_uploads_used` vs `tracks_used` separately in `download-token`.
*   **Risk:** The "Quota Bypass" (1.3) applies here too. A user could download unlimited Fan-Only tracks if they generate tokens in bulk.

---

## 4. Technical Recommendations

### Security Enhancements
1.  **Atomic Token Redemption:** Move the `is_used` check to a SQL `UPDATE ... RETURNING` statement.
2.  **Strict IP Capture:** Enforce `ip_address` presence in token generation.
3.  **Double-Check Quotas:** Verify subscription status/quota *again* at the moment of download, not just token generation.
4.  **Magic Byte Validation:** Install `file-type` to verify uploads.

### Performance & Scalability
1.  **Database Indexing:** Ensure `download_tokens` is indexed by `token`.
2.  **Rate Limiting:** The current rate limit (30/hour) is reasonable but per-IP. Authenticated rate limiting (per User ID) would be more robust against proxy-hopping.

### Compliance (GDPR/Privacy)
1.  **IP Storage:** You are storing user IP addresses in `download_tokens`. This is PII. Ensure:
    *   It is included in the Privacy Policy.
    *   Old tokens are purged regularly (e.g., via cron) to minimize data retention.

---

## Conclusion
The "Download Security" module requires immediate remediation before production release. The IP locking and Token Replay vulnerabilities undermine the platform's core value proposition ("secure download-only").
