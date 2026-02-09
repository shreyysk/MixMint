# MixMint Database Schema Documentation

This document describes the PostgreSQL schema designed for the MixMint platform. The schema is optimized for Supabase and follows a "Secure Access-Control" first philosophy.

## 1. Core Entities

### `profiles`
The primary table for all users. Roles distinguish between Listeners/Users, DJs, and Admins.
- **Fields**: `id` (references auth.users), `full_name`, `role`.

### `dj_profiles`
Extension of `profiles` for approved partner artists.
- **Fields**: `dj_name`, `slug` (unique), `status` (pending/approved/etc), `bio`.

### `tracks` & `album_packs`
The core content items. 
- **Privacy**: Both include `file_key` representing the private R2 path.
- **Rules**: Minimum prices enforced by check constraints (₹29 for tracks, ₹79 for albums).
- **Exclusivity**: `is_fan_only` flag for Super-Only content.

## 2. Access Control Logic

### `purchases`
Records lifetime ownership of content.
- **Constraint**: Unique on `(user_id, content_id, content_type)` to prevent double-buying.

### `dj_subscriptions`
Tracks active plans (Basic/Pro/Super) for a specific DJ.
- **Quotas**: `tracks_used`, `zip_used`, `fan_uploads_used` are incremented per download.
- **Enforcement**: Access check queries must validate `current_date < expires_at` and `used < quota`.

### `download_tokens`
The security layer for file delivery.
- **Nature**: Short-lived (2-5 mins), single-use tokens.
- **Locking**: Captures `ip_address` on request.

## 3. Economics & Rewards

### Wallets & Ledger
A double-entry-style system to track DJ earnings and platform fees.
- **Wallets**: Linked to `profiles`.
- **Ledger Entries**: Immutable records of every financial movement.

### Points & Referrals
- **Points**: Discount-only loyalty currency.
- **Referrals**: One-way tracking of user-to-user and DJ-to-DJ invitations.

## 4. Key Security Principles
- **No Direct Access**: All file keys point to private R2 storage.
- **Validation-First**: APIs must check `purchases` or `dj_subscriptions` before calling `download_tokens`.
- **Atomic Usage**: `download_tokens` usage must be an atomic `is_used` update.
