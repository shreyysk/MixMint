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
