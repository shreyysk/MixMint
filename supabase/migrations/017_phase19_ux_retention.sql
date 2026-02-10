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
