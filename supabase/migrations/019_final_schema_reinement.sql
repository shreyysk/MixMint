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
