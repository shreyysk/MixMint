# Gap Solutions — Legacy / Experimental Components

This directory contains solutions developed during the project that were explored but not integrated into the main Django application.

## `cf_worker/`

**Cloudflare Worker for Large File Delivery** — An alternative streaming implementation.

### What it does
- Streams files directly from R2 with range request support
- Validates token from query parameter (`?t=...`)
- Returns 206 Partial Content for range requests
- Minimal token validation (no IP/device binding, no checksum verification)

### Why it's not used
The main Django download system (`apps/downloads/views.py`) provides:
- Full token validation with IP + device binding
- SHA-256 checksum verification during streaming
- Kill switch / maintenance mode checks
- Ban list enforcement
- Concurrent connection limiting (max 2)
- Anti-leak throttling for large files
- Download completion audit logging
- Fraud detection integration

The Cloudflare Worker was an early exploration for offloading bandwidth from Django, but the security feature parity would require significant additional work. The current Django streaming proxy (`download_content` in `apps/downloads/views.py`) is the production implementation.

### Status
**Archived / Reference only.** Not deployed. The Django download proxy handles all production file delivery.