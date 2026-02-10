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
