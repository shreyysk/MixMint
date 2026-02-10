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
