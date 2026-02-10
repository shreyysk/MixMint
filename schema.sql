-- MixMint Master Schema Definition
-- Optimized for Supabase (Auth, RLS, Realtime)
-- Consolidated from migrations 001-014

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. ENUMS
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('user', 'dj', 'admin', 'moderator');
    CREATE TYPE dj_status AS ENUM ('pending', 'approved', 'rejected', 'banned');
    CREATE TYPE content_type AS ENUM ('track', 'zip');
    CREATE TYPE subscription_plan AS ENUM ('basic', 'pro', 'super');
    CREATE TYPE ledger_entry_type AS ENUM ('credit', 'debit');
    CREATE TYPE ab_test_status AS ENUM ('draft', 'active', 'paused', 'completed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 3. CORE TABLES

-- Profiles (Base User Data)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
    full_name TEXT NOT NULL,
    role user_role DEFAULT 'user' NOT NULL,
    avatar_url TEXT,
    referral_code TEXT UNIQUE,
    points_balance INT DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- DJ Profiles (Storefronts)
CREATE TABLE IF NOT EXISTS public.dj_profiles (
    id UUID REFERENCES public.profiles(id) ON DELETE CASCADE PRIMARY KEY,
    dj_name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    bio TEXT,
    social_links JSONB DEFAULT '{}'::jsonb,
    status dj_status DEFAULT 'pending' NOT NULL,
    payout_details JSONB DEFAULT '{}'::jsonb,
    location TEXT,
    popularity_score INT DEFAULT 0,
    genres TEXT[],
    total_revenue DECIMAL(12,2) DEFAULT 0.00 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Tracks
CREATE TABLE IF NOT EXISTS public.tracks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    dj_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL CHECK (price >= 29.00 OR price = 0),
    file_key TEXT NOT NULL,
    cover_url TEXT,
    duration_sec INT,
    bpm INT,
    genre TEXT,
    is_fan_only BOOLEAN DEFAULT false NOT NULL,
    download_count INT DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Track Previews (YouTube/Instagram)
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

-- Track Versions (for Anti-Piracy/History)
CREATE TABLE IF NOT EXISTS public.track_versions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE NOT NULL,
    version_label TEXT NOT NULL,
    file_key TEXT NOT NULL,
    checksum TEXT,
    is_current BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Album Packs (ZIPs)
CREATE TABLE IF NOT EXISTS public.album_packs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    dj_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL CHECK (price >= 79.00),
    file_key TEXT NOT NULL,
    is_fan_only BOOLEAN DEFAULT false NOT NULL,
    upload_method TEXT CHECK (upload_method IN ('system_generated', 'direct_zip')) DEFAULT 'direct_zip',
    original_file_key TEXT,
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'queued')),
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    processing_error TEXT,
    track_count INTEGER DEFAULT 0,
    total_duration INTEGER,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Album Tracks (for System-Generated ZIPs)
CREATE TABLE IF NOT EXISTS public.album_tracks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    album_id UUID REFERENCES public.album_packs(id) ON DELETE CASCADE NOT NULL,
    track_order INTEGER NOT NULL,
    title TEXT NOT NULL,
    original_file_key TEXT,
    processed_filename TEXT,
    duration INTEGER,
    file_size BIGINT,
    format TEXT DEFAULT 'mp3',
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Album Processing Queue
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

-- 4. COMMERCE & REWARDS

-- Wallets
CREATE TABLE IF NOT EXISTS public.wallets (
    id UUID REFERENCES public.profiles(id) ON DELETE CASCADE PRIMARY KEY,
    balance DECIMAL(12,2) DEFAULT 0.00 NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Points
CREATE TABLE IF NOT EXISTS public.points (
    id UUID REFERENCES public.profiles(id) ON DELETE CASCADE PRIMARY KEY,
    balance INT DEFAULT 0 NOT NULL,
    lifetime_earned INT DEFAULT 0 NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Purchases
CREATE TABLE IF NOT EXISTS public.purchases (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    content_id UUID NOT NULL,
    content_type content_type NOT NULL,
    price_paid DECIMAL(10,2) NOT NULL,
    platform_fee DECIMAL(10,2) DEFAULT 0.00 NOT NULL,
    dj_earnings DECIMAL(10,2) DEFAULT 0.00 NOT NULL,
    payment_id TEXT UNIQUE NOT NULL,
    payment_order_id TEXT,
    seller_id UUID REFERENCES public.dj_profiles(id) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(user_id, content_id, content_type)
);

-- Ledger Entries
CREATE TABLE IF NOT EXISTS public.ledger_entries (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    wallet_id UUID REFERENCES public.wallets(id) ON DELETE CASCADE NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    type ledger_entry_type NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Points History (Ledger)
CREATE TABLE IF NOT EXISTS public.points_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    amount INT NOT NULL,
    type TEXT NOT NULL, -- 'purchase_reward', 'referral_bonus', 'redemption', 'refund'
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Referrals
CREATE TABLE IF NOT EXISTS public.referrals (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    referrer_id UUID REFERENCES public.profiles(id) NOT NULL,
    referred_id UUID REFERENCES public.profiles(id) NOT NULL,
    referral_code TEXT NOT NULL,
    status TEXT DEFAULT 'pending' NOT NULL, -- 'pending', 'converted'
    points_awarded BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(referred_id)
);

-- 5. SOCIAL & COMMUNITY

-- Follows
CREATE TABLE IF NOT EXISTS public.follows (
    follower_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    followed_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (follower_id, followed_id)
);

-- Wishlists
CREATE TABLE IF NOT EXISTS public.wishlists (
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    content_id UUID NOT NULL, 
    content_type content_type NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (user_id, content_id, content_type)
);

-- Reviews
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

-- 6. SYSTEM & ADMINISTRATION

-- System Settings
CREATE TABLE IF NOT EXISTS public.system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Monetization Settings
CREATE TABLE IF NOT EXISTS public.monetization_settings (
    dj_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE PRIMARY KEY,
    revenue_share_pct DECIMAL(5,2) DEFAULT 88.00 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Audit Logs
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    admin_id UUID REFERENCES public.profiles(id),
    action TEXT NOT NULL,
    target_id UUID,
    metadata JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Maintenance Log
CREATE TABLE IF NOT EXISTS public.maintenance_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    ended_at TIMESTAMPTZ,
    reason TEXT,
    conducted_by UUID REFERENCES public.profiles(id)
);

-- 7. A/B TESTING ENGINE

CREATE TABLE IF NOT EXISTS public.ab_tests (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status ab_test_status DEFAULT 'draft' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.ab_test_variants (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    test_id UUID REFERENCES public.ab_tests(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    config JSONB DEFAULT '{}'::jsonb NOT NULL,
    traffic_pct INT NOT NULL CHECK (traffic_pct >= 0 AND traffic_pct <= 100),
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.ab_test_events (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    test_id UUID REFERENCES public.ab_tests(id) ON DELETE CASCADE NOT NULL,
    variant_id UUID REFERENCES public.ab_test_variants(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL, -- 'view', 'click', 'conversion'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 8. SECURITY & TOKENS

-- Download Tokens
CREATE TABLE IF NOT EXISTS public.download_tokens (
    token TEXT PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    content_id UUID NOT NULL,
    content_type content_type NOT NULL,
    ip_address INET,
    user_agent TEXT,
    is_used BOOLEAN DEFAULT false NOT NULL,
    access_source TEXT NOT NULL, -- 'purchase' or 'subscription'
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 9. FUNCTIONS & TRIGGERS

-- Handle New User profile creation
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, role)
  VALUES (new.id, new.raw_user_meta_data->>'full_name', 'user');

  INSERT INTO public.wallets (id, balance)
  VALUES (new.id, 0.00);

  INSERT INTO public.points (id, balance)
  VALUES (new.id, 0);

  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger for profile creation
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- Helper to increment points
CREATE OR REPLACE FUNCTION public.increment_points_balance(target_id UUID, amount INT)
RETURNS VOID AS $$
BEGIN
    UPDATE public.points
    SET balance = balance + amount,
        updated_at = now()
    WHERE id = target_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 10. INDEXES
CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);
CREATE INDEX IF NOT EXISTS idx_dj_profiles_slug ON public.dj_profiles(slug);
CREATE INDEX IF NOT EXISTS idx_tracks_dj ON public.tracks(dj_id);
CREATE INDEX IF NOT EXISTS idx_tracks_genre ON public.tracks(genre);
CREATE INDEX IF NOT EXISTS idx_purchases_user ON public.purchases(user_id);
CREATE INDEX IF NOT EXISTS idx_purchases_seller ON public.purchases(seller_id);
CREATE INDEX IF NOT EXISTS idx_points_history_profile ON public.points_history(profile_id);
CREATE INDEX IF NOT EXISTS idx_download_tokens_token ON public.download_tokens(token);
CREATE INDEX IF NOT EXISTS idx_download_tokens_expiry ON public.download_tokens(expires_at) WHERE is_used = false;
CREATE INDEX IF NOT EXISTS idx_ab_test_events_test ON public.ab_test_events(test_id);
CREATE INDEX IF NOT EXISTS idx_album_packs_processing ON public.album_packs(processing_status) WHERE processing_status != 'completed';

-- 11. ENABLE RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dj_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.album_packs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.points ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.points_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ledger_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ab_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ab_test_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ab_test_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_settings ENABLE ROW LEVEL SECURITY;

-- Default policies (Admin full access, Public limited access)
CREATE POLICY "Public read approved DJs" ON public.dj_profiles FOR SELECT USING (status = 'approved');
CREATE POLICY "Public read tracks" ON public.tracks FOR SELECT USING (true);
CREATE POLICY "Public read album packs" ON public.album_packs FOR SELECT USING (true);
CREATE POLICY "Admins full access profiles" ON public.profiles FOR ALL TO authenticated USING (auth.jwt()->>'role' = 'admin');
CREATE POLICY "DJs manage own tracks" ON public.tracks FOR ALL TO authenticated USING (dj_id = auth.uid());
