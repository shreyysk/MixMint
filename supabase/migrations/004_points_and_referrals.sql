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
