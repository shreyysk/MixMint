-- ============================================
-- MixMint RLS Policies for Public Access
-- ============================================
-- Purpose: Allow anonymous users to view approved content
-- Date: 2026-02-03
-- ============================================

-- 1. Enable RLS on dj_profiles (if not already enabled)
ALTER TABLE dj_profiles ENABLE ROW LEVEL SECURITY;

-- 2. Allow public read access to APPROVED DJ profiles
CREATE POLICY "Public can view approved DJ profiles"
ON dj_profiles FOR SELECT
TO anon, authenticated
USING (status = 'approved');

-- 3. Enable RLS on tracks
ALTER TABLE tracks ENABLE ROW LEVEL SECURITY;

-- 4. Allow public read access to ACTIVE tracks
CREATE POLICY "Public can view active tracks"
ON tracks FOR SELECT
TO anon, authenticated
USING (status = 'active');

-- 5. Enable RLS on album_packs
ALTER TABLE album_packs ENABLE ROW LEVEL SECURITY;

-- 6. Allow public read access to album packs
CREATE POLICY "Public can view album packs"
ON album_packs FOR SELECT
TO anon, authenticated
USING (true);

-- 7. Enable RLS on profiles (for basic user info)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- 8. Allow public read access to profiles (for DJ names, avatars)
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
