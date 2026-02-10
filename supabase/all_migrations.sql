-- ============================================
-- MixMint Schema Migration: Album Packs Consistency
-- ============================================
-- Purpose: Standardize album_packs to use dj_profiles.id
-- Strategy: Non-breaking (keep existing column)
-- Date: 2026-02-03
-- ============================================

-- STEP 1: Add new column for dj_profile reference
ALTER TABLE album_packs 
ADD COLUMN IF NOT EXISTS dj_profile_id UUID;

-- STEP 2: Populate new column by looking up dj_profiles.id from profiles.user_id
UPDATE album_packs 
SET dj_profile_id = (
  SELECT dp.id 
  FROM dj_profiles dp
  WHERE dp.user_id = album_packs.dj_id
)
WHERE dj_profile_id IS NULL;

-- STEP 3: Verify data integrity (should return 0)
-- Run this manually: SELECT COUNT(*) FROM album_packs WHERE dj_profile_id IS NULL;

-- STEP 4: Add foreign key constraint
ALTER TABLE album_packs
DROP CONSTRAINT IF EXISTS fk_album_packs_dj_profile;

ALTER TABLE album_packs
ADD CONSTRAINT fk_album_packs_dj_profile
FOREIGN KEY (dj_profile_id) REFERENCES dj_profiles(id)
ON DELETE CASCADE;

-- STEP 5: Create index for performance
CREATE INDEX IF NOT EXISTS idx_album_packs_dj_profile_id 
ON album_packs(dj_profile_id);

-- ============================================
-- VERIFICATION QUERIES (Run after migration)
-- ============================================

-- Check all albums have dj_profile_id populated
-- SELECT id, title, dj_id, dj_profile_id FROM album_packs LIMIT 10;

-- Verify FK relationships
-- SELECT 
--   ap.id, 
--   ap.title, 
--   dp.dj_name,
--   p.full_name
-- FROM album_packs ap
-- LEFT JOIN dj_profiles dp ON ap.dj_profile_id = dp.id
-- LEFT JOIN profiles p ON ap.dj_id = p.id
-- LIMIT 10;

-- ============================================
-- ROLLBACK PLAN (If needed)
-- ============================================
-- DROP INDEX IF EXISTS idx_album_packs_dj_profile_id;
-- ALTER TABLE album_packs DROP CONSTRAINT IF EXISTS fk_album_packs_dj_profile;
-- ALTER TABLE album_packs DROP COLUMN IF EXISTS dj_profile_id;

-- ============================================
-- NOTE: Do NOT drop dj_id column in this migration
-- We keep both columns for backwards compatibility
-- Future batch will handle cleanup after validation period
-- ============================================
-- ============================================
-- MixMint System Settings Table
-- ============================================
-- Purpose: Store admin-controlled configuration
-- - Payment gateway selection
-- - Feature flags
-- - System-wide settings
-- Date: 2026-02-03
-- ============================================

-- Create system_settings table
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES profiles(id)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_system_settings_updated_at 
ON system_settings(updated_at DESC);

-- Insert default payment gateway setting
INSERT INTO system_settings (key, value, description) 
VALUES (
    'payment_gateway',
    '{"provider": "razorpay", "mode": "test"}'::jsonb,
    'Active payment gateway provider and mode'
)
ON CONFLICT (key) DO NOTHING;

-- Insert minimum pricing settings
INSERT INTO system_settings (key, value, description) 
VALUES (
    'minimum_pricing',
    '{"track": 29, "album": 79, "subscription_basic": 49, "subscription_pro": 99, "subscription_super": 199}'::jsonb,
    'Minimum prices for content (in INR)'
)
ON CONFLICT (key) DO NOTHING;

-- Insert feature flags
INSERT INTO system_settings (key, value, description) 
VALUES (
    'feature_flags',
    '{"fan_uploads_enabled": true, "referrals_enabled": false, "custom_domains_enabled": false}'::jsonb,
    'Feature toggles for platform capabilities'
)
ON CONFLICT (key) DO NOTHING;

-- Enable Row Level Security
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;

-- Policy: Only admins can read settings
DROP POLICY IF EXISTS "Admins can read system settings" ON system_settings;
CREATE POLICY "Admins can read system settings"
ON system_settings FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM profiles
        WHERE profiles.id = auth.uid()
        AND profiles.role = 'admin'
    )
);

-- Policy: Only admins can update settings
DROP POLICY IF EXISTS "Admins can update system settings" ON system_settings;
CREATE POLICY "Admins can update system settings"
ON system_settings FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM profiles
        WHERE profiles.id = auth.uid()
        AND profiles.role = 'admin'
    )
);

-- Verification query
SELECT key, value, description FROM system_settings ORDER BY key;
-- ============================================
-- MixMint RLS Policies for Public Access
-- ============================================
-- Purpose: Allow anonymous users to view approved content
-- Date: 2026-02-03
-- ============================================

-- 1. Enable RLS on dj_profiles (if not already enabled)
ALTER TABLE dj_profiles ENABLE ROW LEVEL SECURITY;

-- 2. Allow public read access to APPROVED DJ profiles
DROP POLICY IF EXISTS "Public can view approved DJ profiles" ON dj_profiles;
CREATE POLICY "Public can view approved DJ profiles"
ON dj_profiles FOR SELECT
TO anon, authenticated
USING (status = 'approved');

-- 3. Enable RLS on tracks
ALTER TABLE tracks ENABLE ROW LEVEL SECURITY;

-- 4. Allow public read access to ACTIVE tracks
DROP POLICY IF EXISTS "Public can view active tracks" ON tracks;
CREATE POLICY "Public can view active tracks"
ON tracks FOR SELECT
TO anon, authenticated
USING (status = 'active');

-- 5. Enable RLS on album_packs
ALTER TABLE album_packs ENABLE ROW LEVEL SECURITY;

-- 6. Allow public read access to album packs
DROP POLICY IF EXISTS "Public can view album packs" ON album_packs;
CREATE POLICY "Public can view album packs"
ON album_packs FOR SELECT
TO anon, authenticated
USING (true);

-- 7. Enable RLS on profiles (for basic user info)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- 8. Allow public read access to profiles (for DJ names, avatars)
DROP POLICY IF EXISTS "Public can view profiles" ON profiles;
CREATE POLICY "Public can view profiles"
ON profiles FOR SELECT
TO anon, authenticated
USING (true);

-- ============================================
-- Verification Queries
-- ============================================

-- Check policies
SELECT schemaname, tablename, policyname, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
AND tablename IN ('dj_profiles', 'tracks', 'album_packs', 'profiles')
ORDER BY tablename, policyname;
-- ============================================
-- MixMint Points and Referrals System
-- ============================================
-- Purpose: Track user points and referral growth
-- Date: 2026-02-04
-- ============================================

-- STEP 1: Referral Codes
-- Each user/DJ gets one unique referral code
CREATE TABLE IF NOT EXISTS referral_codes (
    profile_id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
    code TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast code lookups
CREATE INDEX IF NOT EXISTS idx_referral_codes_code ON referral_codes(code);

-- STEP 2: Referrals Tracking
-- Tracks who invited whom and the status of the referral
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    referred_id UUID UNIQUE NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'joined', -- 'joined' (signup), 'verified' (first purchase)
    points_awarded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index to find all referrals for a user
CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id);

-- STEP 3: Points Balances
-- Aggregate points for each user for fast display
CREATE TABLE IF NOT EXISTS user_points (
    profile_id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
    balance INTEGER NOT NULL DEFAULT 0,
    total_earned INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- STEP 4: Points History
-- Audit trail for every point event
CREATE TABLE IF NOT EXISTS points_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    points INTEGER NOT NULL,
    event_type TEXT NOT NULL, -- 'signup', 'purchase', 'referral_signup', 'referral_conversion'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for user's history
CREATE INDEX IF NOT EXISTS idx_points_history_profile_id ON points_history(profile_id DESC);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

-- Enable RLS
ALTER TABLE referral_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE points_history ENABLE ROW LEVEL SECURITY;

-- 1. Referral Codes: Users can see their own code, anyone can see any code (for lookup)
DROP POLICY IF EXISTS "Anyone can look up referral codes" ON referral_codes;
CREATE POLICY "Anyone can look up referral codes"
ON referral_codes FOR SELECT
TO authenticated
USING (true);

-- 2. Referrals: Referrer can see their referrals, referred user can see who referred them
DROP POLICY IF EXISTS "Users can see their related referrals" ON referrals;
CREATE POLICY "Users can see their related referrals"
ON referrals FOR SELECT
TO authenticated
USING (auth.uid() = referrer_id OR auth.uid() = referred_id);

-- 3. User Points: Users can only see their own balance
DROP POLICY IF EXISTS "Users can see their own points balance" ON user_points;
CREATE POLICY "Users can see their own points balance"
ON user_points FOR SELECT
TO authenticated
USING (auth.uid() = profile_id);

-- 4. Points History: Users can only see their own history
DROP POLICY IF EXISTS "Users can see their own points history" ON points_history;
CREATE POLICY "Users can see their own points history"
ON points_history FOR SELECT
TO authenticated
USING (auth.uid() = profile_id);

-- ============================================
-- INITIAL VALUES (Optional: Add for existing users if any)
-- ============================================
-- This will be handled by application logic or a separate script if needed
-- Migration 005: Hardening - Rate Limits & Indexes
-- Description: Adds infrastructure for rate limiting and performance optimizations.

-- 1. Rate Limits Table
-- Used for persistent, distributed rate limiting across serverless functions.
CREATE TABLE IF NOT EXISTS rate_limits (
    key TEXT PRIMARY KEY, -- e.g., 'rl:payment:1.2.3.4'
    count INTEGER DEFAULT 0,
    reset_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Index for automatic cleanup (though we'll do manual cleanup in cron)
CREATE INDEX IF NOT EXISTS idx_rate_limits_reset_at ON rate_limits(reset_at);

-- 2. Performance Indexes
-- Optimize purchase history lookups
CREATE INDEX IF NOT EXISTS idx_purchases_user_id ON purchases(user_id);
CREATE INDEX IF NOT EXISTS idx_purchases_content_id ON purchases(content_id);

-- Optimize subscription checks
CREATE INDEX IF NOT EXISTS idx_dj_subscriptions_user_dj ON dj_subscriptions(user_id, dj_id);
CREATE INDEX IF NOT EXISTS idx_dj_subscriptions_expires_at ON dj_subscriptions(expires_at);

-- Optimize rewards/points lookups
CREATE INDEX IF NOT EXISTS idx_points_history_profile_id ON points_history(profile_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred_id ON referrals(referred_id);
CREATE INDEX IF NOT EXISTS idx_referral_codes_code ON referral_codes(code);

-- 3. RLS for rate_limits
-- Only service role (server-side) should touch this
ALTER TABLE rate_limits ENABLE ROW LEVEL SECURITY;

-- No public access
DROP POLICY IF EXISTS "No public access to rate_limits" ON rate_limits;
CREATE POLICY "No public access to rate_limits" 
ON rate_limits FOR ALL 
TO authenticated 
USING (false);
-- Migration 006: Phase 8 - Premium Features (Fan Uploads & Custom Domains)
-- Description: Adds fields for exclusive content and custom domain support.

-- 1. Add is_fan_only flag to content tables
ALTER TABLE tracks ADD COLUMN IF NOT EXISTS is_fan_only BOOLEAN DEFAULT false;
ALTER TABLE album_packs ADD COLUMN IF NOT EXISTS is_fan_only BOOLEAN DEFAULT false;

-- 2. Add fan_uploads_used to dj_subscriptions and fan_upload_quota
ALTER TABLE dj_subscriptions ADD COLUMN IF NOT EXISTS fan_uploads_used INTEGER DEFAULT 0;
ALTER TABLE dj_subscriptions ADD COLUMN IF NOT EXISTS fan_upload_quota INTEGER DEFAULT 0;

-- 3. Add Custom Domain fields to DJ profiles
ALTER TABLE dj_profiles ADD COLUMN IF NOT EXISTS custom_domain TEXT UNIQUE;
ALTER TABLE dj_profiles ADD COLUMN IF NOT EXISTS domain_verified BOOLEAN DEFAULT false;

-- 3. Create indices for performance
CREATE INDEX IF NOT EXISTS idx_tracks_is_fan_only ON tracks(is_fan_only);
CREATE INDEX IF NOT EXISTS idx_album_packs_is_fan_only ON album_packs(is_fan_only);
CREATE INDEX IF NOT EXISTS idx_dj_profiles_custom_domain ON dj_profiles(custom_domain) WHERE custom_domain IS NOT NULL;

-- 4. Monetization Settings Table (Infrastructure)
CREATE TABLE IF NOT EXISTS monetization_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dj_id UUID REFERENCES dj_profiles(id) ON DELETE CASCADE,
    revenue_share_pct NUMERIC(5,2) DEFAULT 80.00, -- Default 80% to DJ
    discount_codes JSONB DEFAULT '[]',
    bundle_configs JSONB DEFAULT '[]',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Enable RLS on monetization_settings
ALTER TABLE monetization_settings ENABLE ROW LEVEL SECURITY;

-- DJ can view/update their own monetization settings
DROP POLICY IF EXISTS "DJs can manage their own monetization settings" ON monetization_settings;
CREATE POLICY "DJs can manage their own monetization settings"
ON monetization_settings FOR ALL
TO authenticated
USING (dj_id IN (SELECT id FROM dj_profiles WHERE user_id = auth.uid()))
WITH CHECK (dj_id IN (SELECT id FROM dj_profiles WHERE user_id = auth.uid()));

-- Add unique constraint to ensure one setting per DJ
CREATE UNIQUE INDEX IF NOT EXISTS idx_monetization_settings_dj_id ON monetization_settings(dj_id);
-- 007_phase_1_features.sql

-- 1. Track Previews Table
ALTER TABLE public.tracks DROP COLUMN IF EXISTS youtube_url;

CREATE TABLE IF NOT EXISTS public.track_previews (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE NOT NULL,
    preview_type TEXT CHECK (preview_type IN ('youtube', 'instagram', 'soundcloud')) NOT NULL,
    url TEXT NOT NULL,
    embed_id TEXT NOT NULL,
    embed_html TEXT,
    is_primary BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 2. Follows Table
CREATE TABLE IF NOT EXISTS public.follows (
    follower_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    followed_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (follower_id, followed_id)
);

-- 3. Wishlists Table
CREATE TABLE IF NOT EXISTS public.wishlists (
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    content_id UUID NOT NULL, 
    content_type content_type NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (user_id, content_id, content_type)
);

-- 4. Reviews Table
CREATE TABLE IF NOT EXISTS public.reviews (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE NOT NULL,
    rating INT CHECK (rating >= 1 AND rating <= 5) NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(user_id, track_id)
);

-- 5. Additional Discovery Fields
ALTER TABLE public.dj_profiles ADD COLUMN IF NOT EXISTS location TEXT;
ALTER TABLE public.dj_profiles ADD COLUMN IF NOT EXISTS popularity_score INT DEFAULT 0;
ALTER TABLE public.dj_profiles ADD COLUMN IF NOT EXISTS genres TEXT[]; -- Array of genres (e.g. ['House', 'Techno'])

-- 6. Indexes
CREATE INDEX IF NOT EXISTS idx_track_previews_track ON public.track_previews(track_id);
CREATE INDEX IF NOT EXISTS idx_follows_followed ON public.follows(followed_id);
CREATE INDEX IF NOT EXISTS idx_wishlists_user ON public.wishlists(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_track ON public.reviews(track_id);
-- Add user_agent column to download_tokens table for device fingerprinting
ALTER TABLE public.download_tokens 
ADD COLUMN IF NOT EXISTS user_agent TEXT;
-- MixMint Phase 5: Multiple Audio Formats
-- Create a table to store alternate versions of tracks (WAV, AIFF, FLAC, etc.)

DO $$ BEGIN
    CREATE TYPE audio_format AS ENUM ('mp3_320', 'wav', 'aiff', 'flac');
EXCEPTION WHEN duplicate_object THEN null; END $$;

CREATE TABLE IF NOT EXISTS public.track_versions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE NOT NULL,
    format audio_format NOT NULL,
    file_key TEXT NOT NULL,
    file_size BIGINT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(track_id, format) -- Only one version per format per track
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_track_versions_track ON public.track_versions(track_id);

-- Add version_id to download_tokens to support specific version downloads
ALTER TABLE public.download_tokens 
ADD COLUMN IF NOT EXISTS version_id UUID REFERENCES public.track_versions(id) ON DELETE SET NULL;
-- Add cover_url to tracks table for storing album art
ALTER TABLE public.tracks 
ADD COLUMN IF NOT EXISTS cover_url TEXT;

-- Add cover_url to album_packs table as well if missing (just in case)
ALTER TABLE public.album_packs
ADD COLUMN IF NOT EXISTS cover_url TEXT;
-- Migration 011: Comprehensive Feature Expansion
-- Covers: Anti-Piracy (Devices), Social (Comments, Playlists, Feed), Economics (Invoices), and Branding

-- 1. EXTEND TYPES
DO $$ BEGIN
    CREATE TYPE device_status AS ENUM ('authorized', 'revoked', 'banned');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- 2. SECURITY & ANTI-PIRACY
CREATE TABLE IF NOT EXISTS public.user_devices (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    fingerprint TEXT NOT NULL,
    label TEXT, -- e.g., "Chrome on Windows"
    status device_status DEFAULT 'authorized' NOT NULL,
    last_ip INET,
    last_active_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(user_id, fingerprint)
);

CREATE TABLE IF NOT EXISTS public.login_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    ip_address INET NOT NULL,
    user_agent TEXT,
    location_data JSONB,
    is_suspicious BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 3. SOCIAL & COMMUNITY
CREATE TABLE IF NOT EXISTS public.comments (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE,
    album_id UUID REFERENCES public.album_packs(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    parent_id UUID REFERENCES public.comments(id) ON DELETE CASCADE, -- For replies
    is_moderated BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT one_target CHECK (
        (track_id IS NOT NULL AND album_id IS NULL) OR
        (track_id IS NULL AND album_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS public.activity_feed (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL, -- The "actor"
    action_type TEXT NOT NULL, -- 'release', 'follow', 'comment', 'milestone'
    entity_id UUID NOT NULL,
    entity_type TEXT NOT NULL, -- 'track', 'album', 'dj', 'comment'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.playlists (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT true NOT NULL,
    is_collaborative BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.playlist_tracks (
    playlist_id UUID REFERENCES public.playlists(id) ON DELETE CASCADE NOT NULL,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE NOT NULL,
    position INT NOT NULL,
    added_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (playlist_id, track_id)
);

-- 4. CONTENT MANAGEMENT & VERSIONS
-- Extend track_versions to support version types (Radio Edit, etc.)
ALTER TABLE public.track_versions 
ADD COLUMN IF NOT EXISTS version_type TEXT DEFAULT 'original' NOT NULL;

-- Remove the old unique constraint and add a new one including version_type
ALTER TABLE public.track_versions 
DROP CONSTRAINT IF EXISTS track_versions_track_id_format_key;

ALTER TABLE public.track_versions 
DROP CONSTRAINT IF EXISTS track_versions_track_id_version_type_format_key;

ALTER TABLE public.track_versions 
ADD CONSTRAINT track_versions_track_id_version_type_format_key 
UNIQUE(track_id, version_type, format);

-- 5. ECONOMICS & FINANCIALS
CREATE TABLE IF NOT EXISTS public.invoices (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    purchase_id UUID REFERENCES public.purchases(id) ON DELETE SET NULL,
    user_id UUID REFERENCES public.profiles(id) NOT NULL,
    dj_id UUID REFERENCES public.dj_profiles(id) NOT NULL,
    invoice_number TEXT UNIQUE NOT NULL,
    subtotal DECIMAL(12,2) NOT NULL,
    tax_amount DECIMAL(12,2) DEFAULT 0.00 NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    currency TEXT DEFAULT 'INR' NOT NULL,
    status TEXT DEFAULT 'issued' NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.tax_records (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    invoice_id UUID REFERENCES public.invoices(id) ON DELETE CASCADE NOT NULL,
    tax_type TEXT NOT NULL, -- 'GST', 'VAT', 'Sales Tax'
    tax_rate DECIMAL(5,2) NOT NULL,
    tax_amount DECIMAL(12,2) NOT NULL,
    jurisdiction TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 6. BRANDING & CUSTOMIZATION
CREATE TABLE IF NOT EXISTS public.dj_branding (
    dj_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE PRIMARY KEY,
    custom_domain TEXT UNIQUE,
    custom_css TEXT,
    logo_url TEXT,
    banner_url TEXT,
    color_scheme JSONB DEFAULT '{"primary": "#7c3aed", "secondary": "#a78bfa"}'::jsonb,
    fonts JSONB DEFAULT '{"heading": "Inter", "body": "Inter"}'::jsonb,
    layout_preferences JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 7. INDEXES FOR PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_comments_track ON public.comments(track_id);
CREATE INDEX IF NOT EXISTS idx_comments_album ON public.comments(album_id);
CREATE INDEX IF NOT EXISTS idx_activity_feed_user ON public.activity_feed(user_id);
CREATE INDEX IF NOT EXISTS idx_user_devices_user ON public.user_devices(user_id);
CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist ON public.playlist_tracks(playlist_id);
CREATE INDEX IF NOT EXISTS idx_invoices_user ON public.invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_dj ON public.invoices(dj_id);

-- 8. ROW LEVEL SECURITY (RLS)
ALTER TABLE public.user_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_feed ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.playlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.playlist_tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tax_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dj_branding ENABLE ROW LEVEL SECURITY;

-- Basic RLS Policies (to be refined in Phase 2/3)
DO $$ BEGIN
    DROP POLICY IF EXISTS "Users can manage their own devices" ON public.user_devices;
    CREATE POLICY "Users can manage their own devices" ON public.user_devices FOR ALL USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    DROP POLICY IF EXISTS "Public can view comments" ON public.comments;
    CREATE POLICY "Public can view comments" ON public.comments FOR SELECT USING (true);
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    DROP POLICY IF EXISTS "Users can comment" ON public.comments;
    CREATE POLICY "Users can comment" ON public.comments FOR INSERT WITH CHECK (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    DROP POLICY IF EXISTS "Public can view public playlists" ON public.playlists;
    CREATE POLICY "Public can view public playlists" ON public.playlists FOR SELECT USING (is_public = true OR auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN null; END $$;
-- 9. REMOTE REVOCATION & EXPIRY
ALTER TABLE public.tracks ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE public.tracks ADD COLUMN IF NOT EXISTS version_type TEXT DEFAULT 'original';
ALTER TABLE public.album_packs ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE public.purchases ADD COLUMN IF NOT EXISTS is_revoked BOOLEAN DEFAULT false;
ALTER TABLE public.dj_subscriptions ADD COLUMN IF NOT EXISTS is_revoked BOOLEAN DEFAULT false;

-- 10. USER MANAGEMENT
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT false;

-- 11. COMPLIANCE & REPORTS
CREATE TABLE IF NOT EXISTS public.copyright_reports (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    reporter_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE,
    album_id UUID REFERENCES public.album_packs(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    evidence_url TEXT,
    status TEXT DEFAULT 'pending' NOT NULL, -- 'pending', 'reviewed', 'actioned', 'rejected'
    admin_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 12. SUPPORT & ANNOUNCEMENTS
CREATE TABLE IF NOT EXISTS public.support_tickets (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    category TEXT NOT NULL, -- 'technical', 'billing', 'content', 'other'
    priority TEXT DEFAULT 'medium' NOT NULL, -- 'low', 'medium', 'high', 'urgent'
    status TEXT DEFAULT 'open' NOT NULL, -- 'open', 'in_progress', 'resolved', 'closed'
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.announcements (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    target_audience TEXT DEFAULT 'all' NOT NULL, -- 'all', 'djs', 'users'
    active BOOLEAN DEFAULT true,
    starts_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 13. OPERATIONAL
CREATE TABLE IF NOT EXISTS public.feature_flags (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_enabled BOOLEAN DEFAULT false,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);
-- Migration 012: Final Hardening - Global Row Level Security (RLS)
-- Description: Locks down all tables with strict access control.

-- 1. UTILITY FUNCTIONS
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.profiles 
    WHERE id = auth.uid() AND role = 'admin'
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.is_dj()
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.profiles 
    WHERE id = auth.uid() AND role = 'dj'
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. ENABLE RLS ON ALL TABLES
DO $$ 
DECLARE 
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
    LOOP
        EXECUTE 'ALTER TABLE public.' || quote_ident(r.tablename) || ' ENABLE ROW LEVEL SECURITY;';
    END LOOP;
END $$;

-- 3. GLOBAL ADMIN POLICY
-- Grant admins full access to every table
DO $$ 
DECLARE 
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
    LOOP
        EXECUTE 'DROP POLICY IF EXISTS "Admins have full access" ON public.' || quote_ident(r.tablename);
        EXECUTE 'CREATE POLICY "Admins have full access" ON public.' || quote_ident(r.tablename) || 
                ' FOR ALL TO authenticated USING (public.is_admin());';
    END LOOP;
END $$;

-- 4. SPECIFIC USER POLICIES

-- Profiles: Public can view, owner can update
DROP POLICY IF EXISTS "Public profiles are viewable" ON public.profiles;
CREATE POLICY "Public profiles are viewable" ON public.profiles FOR SELECT USING (true);

DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- DJ Profiles: Public can view, DJ can update own
DROP POLICY IF EXISTS "DJ profiles are viewable" ON public.dj_profiles;
CREATE POLICY "DJ profiles are viewable" ON public.dj_profiles FOR SELECT USING (true);

DROP POLICY IF EXISTS "DJs can update own profile" ON public.dj_profiles;
CREATE POLICY "DJs can update own profile" ON public.dj_profiles FOR UPDATE USING (auth.uid() = id);

-- Tracks & Albums: Public can view, DJ can manage own
DROP POLICY IF EXISTS "Tracks are viewable" ON public.tracks;
CREATE POLICY "Tracks are viewable" ON public.tracks FOR SELECT USING (true);

DROP POLICY IF EXISTS "DJs can manage own tracks" ON public.tracks;
CREATE POLICY "DJs can manage own tracks" ON public.tracks FOR ALL USING (auth.uid() = dj_id);

DROP POLICY IF EXISTS "Albums are viewable" ON public.album_packs;
CREATE POLICY "Albums are viewable" ON public.album_packs FOR SELECT USING (true);

DROP POLICY IF EXISTS "DJs can manage own albums" ON public.album_packs;
CREATE POLICY "DJs can manage own albums" ON public.album_packs FOR ALL USING (auth.uid() = dj_id);

-- Purchases & Subscriptions: Owner can view
DROP POLICY IF EXISTS "Users can view own purchases" ON public.purchases;
CREATE POLICY "Users can view own purchases" ON public.purchases FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can view own subscriptions" ON public.dj_subscriptions;
CREATE POLICY "Users can view own subscriptions" ON public.dj_subscriptions FOR SELECT USING (auth.uid() = user_id);

-- Economics: Owner can view
DROP POLICY IF EXISTS "Users can view own points" ON public.user_points;
CREATE POLICY "Users can view own points" ON public.user_points FOR SELECT USING (auth.uid() = profile_id);

DROP POLICY IF EXISTS "Users can view own points history" ON public.points_history;
CREATE POLICY "Users can view own points history" ON public.points_history FOR SELECT USING (auth.uid() = profile_id);

-- Social: Public can view comments/activity, users can manage own
DROP POLICY IF EXISTS "Comments are public" ON public.comments;
CREATE POLICY "Comments are public" ON public.comments FOR SELECT USING (true);

DROP POLICY IF EXISTS "Users can manage own comments" ON public.comments;
CREATE POLICY "Users can manage own comments" ON public.comments FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Activity feed is viewable" ON public.activity_feed;
CREATE POLICY "Activity feed is viewable" ON public.activity_feed FOR SELECT USING (true);

DROP POLICY IF EXISTS "Users can manage own activity" ON public.activity_feed;
CREATE POLICY "Users can manage own activity" ON public.activity_feed FOR ALL USING (auth.uid() = user_id);

-- Support Tickets: Owner can view/manage
DROP POLICY IF EXISTS "Users can manage own tickets" ON public.support_tickets;
CREATE POLICY "Users can manage own tickets" ON public.support_tickets FOR ALL USING (auth.uid() = user_id);

-- System: Public can view announcements
DROP POLICY IF EXISTS "Announcements are public" ON public.announcements;
CREATE POLICY "Announcements are public" ON public.announcements FOR SELECT USING (active = true);

DROP POLICY IF EXISTS "Feature flags are viewable" ON public.feature_flags;
CREATE POLICY "Feature flags are viewable" ON public.feature_flags FOR SELECT USING (true);

-- Anti-Piracy: Owner can view/manage
DROP POLICY IF EXISTS "Users can manage own devices" ON public.user_devices;
CREATE POLICY "Users can manage own devices" ON public.user_devices FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can view own login history" ON public.login_history;
CREATE POLICY "Users can view own login history" ON public.login_history FOR SELECT USING (auth.uid() = user_id);

-- Compliance: Selective access
DROP POLICY IF EXISTS "Users can report content" ON public.copyright_reports;
CREATE POLICY "Users can report content" ON public.copyright_reports FOR INSERT WITH CHECK (auth.uid() = reporter_id);

DROP POLICY IF EXISTS "Users can view own report status" ON public.copyright_reports;
CREATE POLICY "Users can view own report status" ON public.copyright_reports FOR SELECT USING (auth.uid() = reporter_id);

-- Wishlist & Follows: Owner can manage
DROP POLICY IF EXISTS "Users can manage own wishlist" ON public.wishlists;
CREATE POLICY "Users can manage own wishlist" ON public.wishlists FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can manage own follows" ON public.follows;
CREATE POLICY "Users can manage own follows" ON public.follows FOR ALL USING (auth.uid() = follower_id);
-- Migration 013: A/B Testing & Experiments
-- Description: Adds infrastructure for platform experiments and variant tracking.

CREATE TABLE IF NOT EXISTS public.experiments (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'concluded')) NOT NULL,
    conversion_goal TEXT NOT NULL, -- e.g., 'signup', 'purchase', 'subscription'
    config JSONB DEFAULT '{}'::jsonb, -- Store variant details (e.g., button colors, text)
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Variant exposure tracking (Who saw what?)
CREATE TABLE IF NOT EXISTS public.experiment_exposures (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    experiment_id UUID REFERENCES public.experiments(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    variant_name TEXT NOT NULL, -- 'control', 'variant_a', etc.
    ip_address INET,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- RLS for Experiments
ALTER TABLE public.experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.experiment_exposures ENABLE ROW LEVEL SECURITY;

-- Admins can manage experiments
DROP POLICY IF EXISTS "Admins have full access to experiments" ON public.experiments;
CREATE POLICY "Admins have full access to experiments" 
ON public.experiments FOR ALL 
TO authenticated 
USING (public.is_admin());

-- Public (anonymous or auth) can view running experiments to check variant
DROP POLICY IF EXISTS "Public can view running experiments" ON public.experiments;
CREATE POLICY "Public can view running experiments" 
ON public.experiments FOR SELECT 
USING (status = 'running');

-- Users can record their own exposures
DROP POLICY IF EXISTS "Anyone can record exposures" ON public.experiment_exposures;
CREATE POLICY "Anyone can record exposures" 
ON public.experiment_exposures FOR INSERT 
WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_experiments_status ON public.experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiment_exposures_exp_user ON public.experiment_exposures(experiment_id, user_id);
-- ============================================
-- MixMint Album/ZIP Processing Schema
-- ============================================
-- Phase 13: Advanced Album Management
-- ============================================

-- 1. Update album_packs with processing fields
ALTER TABLE public.album_packs 
ADD COLUMN IF NOT EXISTS upload_method TEXT CHECK (upload_method IN ('system_generated', 'direct_zip')) DEFAULT 'direct_zip',
ADD COLUMN IF NOT EXISTS original_file_key TEXT, -- Storage key for original upload
ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'queued')),
ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS processing_completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS processing_error TEXT,
ADD COLUMN IF NOT EXISTS track_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_duration INTEGER; -- in seconds

-- 2. Create album_tracks table (for system-generated ZIPs and tracking metadata)
CREATE TABLE IF NOT EXISTS public.album_tracks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    album_id UUID REFERENCES public.album_packs(id) ON DELETE CASCADE NOT NULL,
    track_order INTEGER NOT NULL,
    
    -- Original uploaded track (if system_generated)
    title TEXT NOT NULL,
    original_file_key TEXT, -- temp/ tracks storage
    processed_filename TEXT, -- name inside the ZIP
    
    -- Metadata
    duration INTEGER, -- seconds
    file_size BIGINT,
    format TEXT DEFAULT 'mp3',
    
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 3. Create processing queue tracker (optional but good for visibility)
CREATE TABLE IF NOT EXISTS public.album_processing_queue (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    album_id UUID REFERENCES public.album_packs(id) ON DELETE CASCADE NOT NULL,
    status TEXT DEFAULT 'queued',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Enable RLS
ALTER TABLE public.album_tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.album_processing_queue ENABLE ROW LEVEL SECURITY;

-- DJ access policies
DROP POLICY IF EXISTS "DJs can manage their own album tracks" ON public.album_tracks;
CREATE POLICY "DJs can manage their own album tracks" ON public.album_tracks
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.album_packs WHERE id = album_tracks.album_id AND dj_id = auth.uid()));

DROP POLICY IF EXISTS "DJs can view their own processing queue" ON public.album_processing_queue;
CREATE POLICY "DJs can view their own processing queue" ON public.album_processing_queue
    FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.album_packs WHERE id = album_processing_queue.album_id AND dj_id = auth.uid()));

-- Indexing
CREATE INDEX IF NOT EXISTS idx_album_tracks_album ON public.album_tracks(album_id);
CREATE INDEX IF NOT EXISTS idx_album_processing_status ON public.album_packs(processing_status);
-- Migration 015: Advanced Analytics & Referral Tiering
-- Phase 17 Implementation

-- 1. Extend Purchases for Analytics
ALTER TABLE public.purchases 
ADD COLUMN IF NOT EXISTS seller_id UUID REFERENCES public.dj_profiles(id),
ADD COLUMN IF NOT EXISTS price_paid DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS dj_earnings DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS ip_address INET,
ADD COLUMN IF NOT EXISTS location_data JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS user_agent TEXT;

-- Populate seller_id for existing records
UPDATE public.purchases p
SET seller_id = COALESCE(
    (SELECT dj_id FROM public.tracks t WHERE t.id = p.content_id),
    (SELECT dj_id FROM public.album_packs a WHERE a.id = p.content_id),
    (SELECT dj_id FROM public.albums al WHERE al.id = p.content_id) -- Handle 'albums' table if it exists
)
WHERE seller_id IS NULL;

-- Backfill price_paid if amount or price exists
DO $$ 
BEGIN 
    -- Check for 'amount' column
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='purchases' AND column_name='amount') THEN
        UPDATE public.purchases SET price_paid = amount WHERE price_paid IS NULL;
    END IF;
    
    -- Check for 'price' column (from user's JSON)
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='purchases' AND column_name='price') THEN
        -- If price is integer (cents), divide by 100. If it's already decimal, just use it.
        UPDATE public.purchases 
        SET price_paid = CASE 
            WHEN (SELECT data_type FROM information_schema.columns WHERE table_name='purchases' AND column_name='price') = 'integer' 
            THEN price::decimal / 100 
            ELSE price::decimal 
        END
        WHERE price_paid IS NULL;
    END IF;

    -- Estimate dj_earnings (default 88%)
    UPDATE public.purchases SET dj_earnings = price_paid * 0.88 WHERE dj_earnings IS NULL AND price_paid IS NOT NULL;
END $$;

-- 2. Extend DJ Referral Tiers
-- Track referral level for tiered rewards (e.g. Bronze, Silver, Gold referrers)
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS referral_tier TEXT DEFAULT 'bronze' CHECK (referral_tier IN ('bronze', 'silver', 'gold', 'platinum'));

-- 3. Analytics Views for DJs
-- Use dynamic SQL (EXECUTE) to prevent parse-time errors in the Supabase editor
DO $$
BEGIN
    EXECUTE 'CREATE OR REPLACE VIEW public.dj_sale_analytics AS
    SELECT 
        seller_id as dj_id,
        content_type,
        COUNT(id) as total_sales,
        SUM(price_paid) as gross_revenue,
        SUM(dj_earnings) as net_earnings,
        location_data->>''country'' as country,
        location_data->>''city'' as city,
        DATE_TRUNC(''day'', created_at) as sale_date
    FROM public.purchases
    GROUP BY seller_id, content_type, country, city, sale_date;';
    
    -- Enable RLS for the view
    EXECUTE 'ALTER VIEW public.dj_sale_analytics SET (security_invoker = on);';
END $$;

-- 4. Referral Tier logic trigger (Optional: for later automation)
-- This could be a cron or a trigger that promotes users based on successful verified referrals
-- Migration 016: Phase 18 - Platform Intelligence & Automation
-- Smart Recommendations, Fraud Detection, Performance Monitoring, Content Moderation

-- 1. USER INTERACTIONS (for Recommendations Engine)
CREATE TABLE IF NOT EXISTS public.user_interactions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE,
    dj_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE,
    interaction_type TEXT NOT NULL CHECK (interaction_type IN ('view', 'purchase', 'wishlist', 'follow_dj', 'play')),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_interactions_user ON public.user_interactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_interactions_track ON public.user_interactions(track_id);
CREATE INDEX IF NOT EXISTS idx_user_interactions_type ON public.user_interactions(interaction_type);

-- 2. DJ ONBOARDING PROGRESS
CREATE TABLE IF NOT EXISTS public.dj_onboarding_progress (
    dj_id UUID PRIMARY KEY REFERENCES public.dj_profiles(id) ON DELETE CASCADE,
    steps_completed JSONB DEFAULT '[]'::jsonb, -- Array of completed step IDs
    email_sequence_stage INTEGER DEFAULT 0, -- Current email in sequence
    last_email_sent_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 3. FRAUD DETECTION
CREATE TABLE IF NOT EXISTS public.fraud_alerts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('referral_abuse', 'download_farming', 'payment_fraud', 'suspicious_activity')),
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    details JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'actioned', 'dismissed')),
    reviewed_by UUID REFERENCES public.profiles(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fraud_alerts_status ON public.fraud_alerts(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_user ON public.fraud_alerts(user_id);

-- 4. PERFORMANCE MONITORING
CREATE TABLE IF NOT EXISTS public.api_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    response_time_ms INTEGER NOT NULL,
    status_code INTEGER NOT NULL,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    ip_address INET,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Partition by day for performance (optional, can be added later)
CREATE INDEX IF NOT EXISTS idx_api_metrics_endpoint ON public.api_metrics(endpoint, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_metrics_slow_queries ON public.api_metrics(response_time_ms DESC) WHERE response_time_ms > 1000;

-- 5. CONTENT MODERATION (Audio Fingerprinting)
CREATE TABLE IF NOT EXISTS public.track_fingerprints (
    track_id UUID PRIMARY KEY REFERENCES public.tracks(id) ON DELETE CASCADE,
    fingerprint TEXT NOT NULL,
    algorithm TEXT DEFAULT 'chromaprint', -- fingerprinting algorithm used
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_track_fingerprints_hash ON public.track_fingerprints(fingerprint);

CREATE TABLE IF NOT EXISTS public.moderation_queue (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('duplicate', 'copyright', 'metadata_suspicious', 'manual_flag')),
    similarity_score DECIMAL(5,2),
    matched_track_id UUID REFERENCES public.tracks(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by UUID REFERENCES public.profiles(id),
    reviewed_at TIMESTAMPTZ,
    admin_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_moderation_queue_status ON public.moderation_queue(status, created_at DESC);

-- 6. RLS POLICIES
ALTER TABLE public.user_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dj_onboarding_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fraud_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.track_fingerprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.moderation_queue ENABLE ROW LEVEL SECURITY;

-- User Interactions: Users can see their own, admins can see all
DROP POLICY IF EXISTS "Users can view own interactions" ON public.user_interactions;
CREATE POLICY "Users can view own interactions" ON public.user_interactions
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own interactions" ON public.user_interactions;
CREATE POLICY "Users can insert own interactions" ON public.user_interactions
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- DJ Onboarding: DJs can see their own progress
DROP POLICY IF EXISTS "DJs can view own onboarding" ON public.dj_onboarding_progress;
CREATE POLICY "DJs can view own onboarding" ON public.dj_onboarding_progress
    FOR SELECT TO authenticated
    USING (auth.uid() = dj_id);

-- Fraud Alerts: Admin only
DROP POLICY IF EXISTS "Admins can manage fraud alerts" ON public.fraud_alerts;
CREATE POLICY "Admins can manage fraud alerts" ON public.fraud_alerts
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));

-- API Metrics: Admin only
DROP POLICY IF EXISTS "Admins can view metrics" ON public.api_metrics;
CREATE POLICY "Admins can view metrics" ON public.api_metrics
    FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));

-- Moderation Queue: Admin only
DROP POLICY IF EXISTS "Admins can manage moderation queue" ON public.moderation_queue;
CREATE POLICY "Admins can manage moderation queue" ON public.moderation_queue
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));
-- Migration 017: Phase 19 - User Experience & Retention
-- Wishlist Notifications, DJ Milestones, Activity Feed, Advanced Search, Playlists

-- 1. WISHLIST PRICE TRACKING
CREATE TABLE IF NOT EXISTS public.wishlist_price_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wishlist_price_history_track ON public.wishlist_price_history(track_id, recorded_at DESC);

-- Add notification preferences to profiles
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS notification_preferences JSONB DEFAULT '{
    "wishlist_price_drop": true,
    "wishlist_free": true,
    "followed_dj_release": true,
    "dj_milestone": true
}'::jsonb;

-- 2. DJ MILESTONES
CREATE TABLE IF NOT EXISTS public.dj_milestones (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    dj_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE NOT NULL,
    milestone_type TEXT NOT NULL CHECK (milestone_type IN (
        'first_sale', 'downloads_100', 'downloads_500', 'downloads_1000',
        'revenue_1000', 'revenue_10000', 'revenue_50000', 'revenue_100000',
        'followers_10', 'followers_50', 'followers_100', 'followers_500', 'followers_1000',
        'uploads_10', 'uploads_25', 'uploads_50', 'uploads_100'
    )),
    achieved_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    notified BOOLEAN DEFAULT false,
    UNIQUE(dj_id, milestone_type)
);

CREATE INDEX IF NOT EXISTS idx_dj_milestones_dj ON public.dj_milestones(dj_id);
CREATE INDEX IF NOT EXISTS idx_dj_milestones_unnotified ON public.dj_milestones(notified) WHERE notified = false;

-- 3. USER ACTIVITY FEED
CREATE TABLE IF NOT EXISTS public.activity_feed (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    activity_type TEXT NOT NULL,
    content JSONB NOT NULL,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Upgrade activity_feed if it was created in 011 with different columns
ALTER TABLE public.activity_feed ADD COLUMN IF NOT EXISTS activity_type TEXT;
ALTER TABLE public.activity_feed ADD COLUMN IF NOT EXISTS content JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.activity_feed ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT false;

-- Fix Index naming conflict with 011
DROP INDEX IF EXISTS idx_activity_feed_user;
CREATE INDEX idx_activity_feed_user ON public.activity_feed(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_feed_unread ON public.activity_feed(user_id, is_read) WHERE is_read = false;

-- 4. PLAYLISTS & COLLECTIONS
CREATE TABLE IF NOT EXISTS public.playlists (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_smart BOOLEAN DEFAULT false,
    smart_criteria JSONB,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Handle name/title drift from 011
DO $$ 
BEGIN 
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='playlists' AND column_name='title') THEN
        ALTER TABLE public.playlists RENAME COLUMN title TO name;
    END IF;
END $$;

ALTER TABLE public.playlists ADD COLUMN IF NOT EXISTS is_smart BOOLEAN DEFAULT false;
ALTER TABLE public.playlists ADD COLUMN IF NOT EXISTS smart_criteria JSONB;

CREATE TABLE IF NOT EXISTS public.playlist_tracks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    playlist_id UUID REFERENCES public.playlists(id) ON DELETE CASCADE NOT NULL,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE NOT NULL,
    position INTEGER NOT NULL,
    added_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(playlist_id, track_id)
);

CREATE INDEX IF NOT EXISTS idx_playlists_user ON public.playlists(user_id);
CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist ON public.playlist_tracks(playlist_id, position);

-- 5. RLS POLICIES
ALTER TABLE public.wishlist_price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dj_milestones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_feed ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.playlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.playlist_tracks ENABLE ROW LEVEL SECURITY;

-- Wishlist Price History: Public read (for price tracking)
DROP POLICY IF EXISTS "Anyone can view price history" ON public.wishlist_price_history;
CREATE POLICY "Anyone can view price history" ON public.wishlist_price_history
    FOR SELECT TO authenticated
    USING (true);

-- DJ Milestones: DJs can view their own
DROP POLICY IF EXISTS "DJs can view own milestones" ON public.dj_milestones;
CREATE POLICY "DJs can view own milestones" ON public.dj_milestones
    FOR SELECT TO authenticated
    USING (auth.uid() = dj_id);

-- Activity Feed: Users can view and update their own
DROP POLICY IF EXISTS "Users can view own feed" ON public.activity_feed;
CREATE POLICY "Users can view own feed" ON public.activity_feed
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own feed" ON public.activity_feed;
CREATE POLICY "Users can update own feed" ON public.activity_feed
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id);

-- Playlists: Users can manage their own
DROP POLICY IF EXISTS "Users can view own playlists" ON public.playlists;
CREATE POLICY "Users can view own playlists" ON public.playlists
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id OR is_public = true);

DROP POLICY IF EXISTS "Users can manage own playlists" ON public.playlists;
CREATE POLICY "Users can manage own playlists" ON public.playlists
    FOR ALL TO authenticated
    USING (auth.uid() = user_id);

-- Playlist Tracks: Users can manage their own playlist tracks
DROP POLICY IF EXISTS "Users can manage own playlist tracks" ON public.playlist_tracks;
CREATE POLICY "Users can manage own playlist tracks" ON public.playlist_tracks
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.playlists
            WHERE playlists.id = playlist_tracks.playlist_id
            AND playlists.user_id = auth.uid()
        )
    );

-- 6. FUNCTIONS FOR AUTOMATION

-- Function to check and record DJ milestones
CREATE OR REPLACE FUNCTION check_dj_milestones(dj_uuid UUID)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    total_sales INTEGER;
    total_downloads INTEGER;
    total_revenue DECIMAL(10,2);
    total_followers INTEGER;
    total_uploads INTEGER;
BEGIN
    -- Get DJ stats
    SELECT COUNT(*) INTO total_sales
    FROM purchases WHERE seller_id = dj_uuid;
    
    SELECT COALESCE(SUM(download_count), 0) INTO total_downloads
    FROM tracks WHERE dj_id = dj_uuid;
    
    SELECT COALESCE(SUM(dj_earnings), 0) INTO total_revenue
    FROM purchases WHERE seller_id = dj_uuid;
    
    SELECT COUNT(*) INTO total_followers
    FROM follows WHERE followed_id = dj_uuid;
    
    SELECT COUNT(*) INTO total_uploads
    FROM tracks WHERE dj_id = dj_uuid;
    
    -- Check and insert milestones
    IF total_sales >= 1 THEN
        INSERT INTO dj_milestones (dj_id, milestone_type)
        VALUES (dj_uuid, 'first_sale')
        ON CONFLICT (dj_id, milestone_type) DO NOTHING;
    END IF;
    
    IF total_downloads >= 100 THEN
        INSERT INTO dj_milestones (dj_id, milestone_type)
        VALUES (dj_uuid, 'downloads_100')
        ON CONFLICT (dj_id, milestone_type) DO NOTHING;
    END IF;
    
    IF total_downloads >= 500 THEN
        INSERT INTO dj_milestones (dj_id, milestone_type)
        VALUES (dj_uuid, 'downloads_500')
        ON CONFLICT (dj_id, milestone_type) DO NOTHING;
    END IF;
    
    IF total_revenue >= 1000 THEN
        INSERT INTO dj_milestones (dj_id, milestone_type)
        VALUES (dj_uuid, 'revenue_1000')
        ON CONFLICT (dj_id, milestone_type) DO NOTHING;
    END IF;
    
    IF total_revenue >= 10000 THEN
        INSERT INTO dj_milestones (dj_id, milestone_type)
        VALUES (dj_uuid, 'revenue_10000')
        ON CONFLICT (dj_id, milestone_type) DO NOTHING;
    END IF;
    
    IF total_followers >= 10 THEN
        INSERT INTO dj_milestones (dj_id, milestone_type)
        VALUES (dj_uuid, 'followers_10')
        ON CONFLICT (dj_id, milestone_type) DO NOTHING;
    END IF;
    
    IF total_uploads >= 10 THEN
        INSERT INTO dj_milestones (dj_id, milestone_type)
        VALUES (dj_uuid, 'uploads_10')
        ON CONFLICT (dj_id, milestone_type) DO NOTHING;
    END IF;
END;
$$;
-- Migration 018: Phase 20 - Mobile & PWA
-- Push Subscriptions for browser notifications

CREATE TABLE IF NOT EXISTS public.push_subscriptions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    endpoint TEXT NOT NULL,
    keys JSONB NOT NULL, -- {p256dh, auth}
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    last_used TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(user_id, endpoint)
);

CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user ON public.push_subscriptions(user_id);

-- Add offline caching flag to purchases
ALTER TABLE public.purchases
ADD COLUMN IF NOT EXISTS cached_offline BOOLEAN DEFAULT false;

-- RLS Policies
ALTER TABLE public.push_subscriptions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage own push subscriptions" ON public.push_subscriptions;
CREATE POLICY "Users can manage own push subscriptions" ON public.push_subscriptions
    FOR ALL TO authenticated
    USING (auth.uid() = user_id);
-- Migration 019: Final Schema Refinement & RLS Stabilization
-- Description: Standardizes naming, removes redundancies, and fixes RLS entity ownership logic.

-- 1. UTILITY FUNCTIONS
-- Function to check if current user is owner of a content (using dj_profiles.id)
CREATE OR REPLACE FUNCTION public.is_content_owner(dj_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.dj_profiles 
    WHERE id = dj_uuid AND user_id = auth.uid()
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. REDUNDANT TABLE CLEANUP
-- Use CASCADE to drop 'albums' even if 'album_tracks' depends on it.
-- Then we ensure 'album_tracks' points to 'album_packs'.
DROP TABLE IF EXISTS public.albums CASCADE;

DO $$ 
BEGIN
    -- If album_tracks exists, we ensure its album_id points to the correct table (album_packs)
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'album_tracks' AND schemaname = 'public') THEN
        -- Drop any incorrect foreign keys if they persist
        ALTER TABLE public.album_tracks DROP CONSTRAINT IF EXISTS album_tracks_album_id_fkey;
        
        -- Add/Confirm the correct foreign key to album_packs
        ALTER TABLE public.album_tracks 
        ADD CONSTRAINT album_tracks_album_id_fkey 
        FOREIGN KEY (album_id) REFERENCES public.album_packs(id) ON DELETE CASCADE;
    END IF;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- 3. ACTIVITY FEED STANDARDIZATION
-- Merge activity_type -> action_type and content -> metadata if they already exist
DO $$ 
BEGIN 
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='activity_feed' AND column_name='activity_type') THEN
        UPDATE public.activity_feed SET action_type = activity_type WHERE action_type IS NULL OR action_type = '';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='activity_feed' AND column_name='content') THEN
        UPDATE public.activity_feed SET metadata = (metadata || content) WHERE content IS NOT NULL;
    END IF;
END $$;

-- Drop the redundant columns after data merge
ALTER TABLE public.activity_feed DROP COLUMN IF EXISTS activity_type;
ALTER TABLE public.activity_feed DROP COLUMN IF EXISTS content;

-- 4. PLAYLIST STANDARDIZATION
-- Ensure 'name' is the consistent column (previously handled rename in 017, but ensuring column matches spec)
ALTER TABLE public.playlists ALTER COLUMN name SET NOT NULL;

-- 5. RLS NUKE & REBUILD (For Consistency)
-- We nuke existing policies on core tables to prevent "Policy name already exists" or overlapping logic.
DO $$ 
DECLARE 
    r RECORD;
BEGIN
    FOR r IN (
        SELECT policyname, tablename 
        FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename IN ('tracks', 'album_packs', 'profiles', 'dj_profiles')
    ) 
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', r.policyname, r.tablename);
    END LOOP;
END $$;

-- 6. RE-APPLY HARDENED POLICIES

-- Profiles
CREATE POLICY "Public profiles are viewable" ON public.profiles FOR SELECT USING (true);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- DJ Profiles
CREATE POLICY "Public can view approved DJ profiles" ON public.dj_profiles FOR SELECT USING (status = 'approved');
CREATE POLICY "DJs can update own profile" ON public.dj_profiles FOR UPDATE USING (auth.uid() = user_id);

-- Tracks
CREATE POLICY "Public tracks are viewable" ON public.tracks FOR SELECT USING (status = 'active');
CREATE POLICY "DJs can manage own tracks" ON public.tracks FOR ALL USING (public.is_content_owner(dj_id));

-- Album Packs
CREATE POLICY "Public albums are viewable" ON public.album_packs FOR SELECT USING (true);
CREATE POLICY "DJs can manage own albums" ON public.album_packs FOR ALL USING (public.is_content_owner(dj_id));

-- 7. GLOBAL ADMIN ACCESS (Ensuring it persists after nuke)
DO $$ 
DECLARE 
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS "Admins have full access" ON public.%I', r.tablename);
        EXECUTE format('CREATE POLICY "Admins have full access" ON public.%I FOR ALL TO authenticated USING (public.is_admin())', r.tablename);
    END LOOP;
END $$;
-- Create admin_audit_logs table
create table if not exists admin_audit_logs (
    id uuid default uuid_generate_v4() primary key,
    admin_id uuid references auth.users(id) not null,
    action_type text not null, -- e.g., 'update_setting', 'ban_user', 'approve_dj'
    entity_type text not null, -- e.g., 'user', 'track', 'system'
    entity_id text,
    details jsonb, -- Stores changes or extra info
    ip_address text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS Policies
alter table admin_audit_logs enable row level security;

-- Only admins can view audit logs
drop policy if exists "Admins can view audit logs" on admin_audit_logs;
create policy "Admins can view audit logs"
    on admin_audit_logs
    for select
    using (
        exists (
            select 1 from profiles
            where profiles.id = auth.uid()
            and profiles.role = 'admin'
        )
    );

-- Only system/admins can insert (via API)
drop policy if exists "Admins can insert audit logs" on admin_audit_logs;
create policy "Admins can insert audit logs"
    on admin_audit_logs
    for insert
    with check (
        exists (
            select 1 from profiles
            where profiles.id = auth.uid()
            and profiles.role = 'admin'
        )
    );
