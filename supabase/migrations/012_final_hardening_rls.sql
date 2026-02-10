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
