-- MixMint Master Schema Definition
-- Optimized for Supabase (Auth, RLS, Realtime)

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. ENUMS
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('user', 'dj', 'admin');
    CREATE TYPE dj_status AS ENUM ('pending', 'approved', 'rejected', 'banned');
    CREATE TYPE content_type AS ENUM ('track', 'zip');
    CREATE TYPE subscription_plan AS ENUM ('basic', 'pro', 'super');
    CREATE TYPE ledger_entry_type AS ENUM ('credit', 'debit');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;
-- Profiles (Base User Data)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
    full_name TEXT NOT NULL,
    role user_role DEFAULT 'user' NOT NULL,
    avatar_url TEXT,
    referral_code TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Ensure wallets and points are created for new users
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

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- DJ Profiles (Storefronts)
CREATE TABLE IF NOT EXISTS public.dj_profiles (
    id UUID REFERENCES public.profiles(id) ON DELETE CASCADE PRIMARY KEY,
    dj_name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    bio TEXT,
    social_links JSONB DEFAULT '{}'::jsonb,
    status dj_status DEFAULT 'pending' NOT NULL,
    payout_details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Tracks
CREATE TABLE IF NOT EXISTS public.tracks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    dj_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL CHECK (price >= 29.00 OR price = 0), -- 0 for promotional free
    file_key TEXT NOT NULL,
    duration_sec INT,
    bpm INT,
    genre TEXT,
    youtube_url TEXT,
    is_fan_only BOOLEAN DEFAULT false NOT NULL,
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
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 4. ACCESS CONTROL

-- Purchases
CREATE TABLE IF NOT EXISTS public.purchases (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    content_id UUID NOT NULL,
    content_type content_type NOT NULL,
    price_paid DECIMAL(10,2) NOT NULL,
    payment_id TEXT UNIQUE NOT NULL,
    payment_order_id TEXT,
    seller_id UUID REFERENCES public.dj_profiles(id) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(user_id, content_id, content_type) -- Prevent duplicate purchases
);

-- DJ Subscriptions
CREATE TABLE IF NOT EXISTS public.dj_subscriptions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    dj_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE NOT NULL,
    plan subscription_plan NOT NULL,
    track_quota INT NOT NULL,
    tracks_used INT DEFAULT 0 NOT NULL,
    zip_quota INT NOT NULL,
    zip_used INT DEFAULT 0 NOT NULL,
    fan_upload_quota INT NOT NULL,
    fan_uploads_used INT DEFAULT 0 NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    payment_id TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(user_id, dj_id) -- One active plan per DJ
);

-- 5. SECURITY & LIMITS

-- Download Tokens (Atomic & Expiring)
CREATE TABLE IF NOT EXISTS public.download_tokens (
    token TEXT PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    content_id UUID NOT NULL,
    content_type content_type NOT NULL,
    ip_address INET,
    is_used BOOLEAN DEFAULT false NOT NULL,
    access_source TEXT NOT NULL, -- 'purchase' or 'subscription'
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 6. ECONOMICS

-- Wallets
CREATE TABLE IF NOT EXISTS public.wallets (
    id UUID REFERENCES public.profiles(id) ON DELETE CASCADE PRIMARY KEY,
    balance DECIMAL(12,2) DEFAULT 0.00 NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
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

-- Points
CREATE TABLE IF NOT EXISTS public.points (
    id UUID REFERENCES public.profiles(id) ON DELETE CASCADE PRIMARY KEY,
    balance INT DEFAULT 0 NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Referrals
CREATE TABLE IF NOT EXISTS public.referrals (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    referrer_id UUID REFERENCES public.profiles(id) NOT NULL,
    referred_id UUID REFERENCES public.profiles(id) NOT NULL,
    referral_code TEXT NOT NULL,
    status TEXT DEFAULT 'pending' NOT NULL,
    points_awarded BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(referred_id) -- One referrer per user
);

-- 7. SYSTEM

-- System Settings
CREATE TABLE IF NOT EXISTS public.system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Monetization Settings (Per DJ overrides)
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
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 8. INDEXES for Performance
CREATE INDEX IF NOT EXISTS idx_download_tokens_expiry ON public.download_tokens(expires_at) WHERE is_used = false;
CREATE INDEX IF NOT EXISTS idx_purchases_user_content ON public.purchases(user_id, content_id, content_type);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON public.dj_subscriptions(user_id, dj_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_tracks_dj ON public.tracks(dj_id);
CREATE INDEX IF NOT EXISTS idx_dj_profiles_slug ON public.dj_profiles(slug);

-- 9. ROW LEVEL SECURITY (RLS) policies would be applied here globally.
-- Example:
-- ALTER TABLE public.tracks ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Public can view tracks" ON public.tracks FOR SELECT USING (true);

    UPDATE public.dj_subscriptions SET %I = %I + 1 WHERE id = $1', field_name, field_name)
    USING sub_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.increment_points_balance(target_id UUID, amount INT)
RETURNS VOID AS $$
BEGIN
    UPDATE public.points
    SET balance = balance + amount,
        updated_at = now()
    WHERE id = target_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Points History (Ledger)
CREATE TABLE IF NOT EXISTS public.points_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    amount INT NOT NULL, -- positive for earn, negative for spend
    type TEXT NOT NULL, -- 'purchase_reward', 'referral_bonus', 'redemption', 'refund'
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Index for points history
CREATE INDEX IF NOT EXISTS idx_points_history_profile ON public.points_history(profile_id);
