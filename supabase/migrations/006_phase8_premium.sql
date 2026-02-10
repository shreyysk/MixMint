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
