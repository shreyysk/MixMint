-- Migration 011: Comprehensive Feature Expansion
-- Covers: Anti-Piracy (Devices), Social (Comments, Playlists, Feed), Economics (Invoices), and Branding

-- 1. EXTEND TYPES
DO $$ BEGIN
    CREATE TYPE device_status AS ENUM ('authorized', 'revoked', 'banned');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- 2. SECURITY & ANTI-PIRACY
CREATE TABLE IF NOT EXISTS public.user_devices (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    fingerprint TEXT NOT NULL,
    label TEXT, -- e.g., "Chrome on Windows"
    status device_status DEFAULT 'authorized' NOT NULL,
    last_ip INET,
    last_active_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(user_id, fingerprint)
);

CREATE TABLE IF NOT EXISTS public.login_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    ip_address INET NOT NULL,
    user_agent TEXT,
    location_data JSONB,
    is_suspicious BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 3. SOCIAL & COMMUNITY
CREATE TABLE IF NOT EXISTS public.comments (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE,
    album_id UUID REFERENCES public.album_packs(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    parent_id UUID REFERENCES public.comments(id) ON DELETE CASCADE, -- For replies
    is_moderated BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT one_target CHECK (
        (track_id IS NOT NULL AND album_id IS NULL) OR
        (track_id IS NULL AND album_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS public.activity_feed (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL, -- The "actor"
    action_type TEXT NOT NULL, -- 'release', 'follow', 'comment', 'milestone'
    entity_id UUID NOT NULL,
    entity_type TEXT NOT NULL, -- 'track', 'album', 'dj', 'comment'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.playlists (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT true NOT NULL,
    is_collaborative BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.playlist_tracks (
    playlist_id UUID REFERENCES public.playlists(id) ON DELETE CASCADE NOT NULL,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE NOT NULL,
    position INT NOT NULL,
    added_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (playlist_id, track_id)
);

-- 4. CONTENT MANAGEMENT & VERSIONS
-- Extend track_versions to support version types (Radio Edit, etc.)
ALTER TABLE public.track_versions 
ADD COLUMN IF NOT EXISTS version_type TEXT DEFAULT 'original' NOT NULL;

-- Remove the old unique constraint and add a new one including version_type
ALTER TABLE public.track_versions 
DROP CONSTRAINT IF EXISTS track_versions_track_id_format_key;

ALTER TABLE public.track_versions 
ADD CONSTRAINT track_versions_track_id_version_type_format_key 
UNIQUE(track_id, version_type, format);

-- 5. ECONOMICS & FINANCIALS
CREATE TABLE IF NOT EXISTS public.invoices (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    purchase_id UUID REFERENCES public.purchases(id) ON DELETE SET NULL,
    user_id UUID REFERENCES public.profiles(id) NOT NULL,
    dj_id UUID REFERENCES public.dj_profiles(id) NOT NULL,
    invoice_number TEXT UNIQUE NOT NULL,
    subtotal DECIMAL(12,2) NOT NULL,
    tax_amount DECIMAL(12,2) DEFAULT 0.00 NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    currency TEXT DEFAULT 'INR' NOT NULL,
    status TEXT DEFAULT 'issued' NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.tax_records (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    invoice_id UUID REFERENCES public.invoices(id) ON DELETE CASCADE NOT NULL,
    tax_type TEXT NOT NULL, -- 'GST', 'VAT', 'Sales Tax'
    tax_rate DECIMAL(5,2) NOT NULL,
    tax_amount DECIMAL(12,2) NOT NULL,
    jurisdiction TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 6. BRANDING & CUSTOMIZATION
CREATE TABLE IF NOT EXISTS public.dj_branding (
    dj_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE PRIMARY KEY,
    custom_domain TEXT UNIQUE,
    custom_css TEXT,
    logo_url TEXT,
    banner_url TEXT,
    color_scheme JSONB DEFAULT '{"primary": "#7c3aed", "secondary": "#a78bfa"}'::jsonb,
    fonts JSONB DEFAULT '{"heading": "Inter", "body": "Inter"}'::jsonb,
    layout_preferences JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 7. INDEXES FOR PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_comments_track ON public.comments(track_id);
CREATE INDEX IF NOT EXISTS idx_comments_album ON public.comments(album_id);
CREATE INDEX IF NOT EXISTS idx_activity_feed_user ON public.activity_feed(user_id);
CREATE INDEX IF NOT EXISTS idx_user_devices_user ON public.user_devices(user_id);
CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist ON public.playlist_tracks(playlist_id);
CREATE INDEX IF NOT EXISTS idx_invoices_user ON public.invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_dj ON public.invoices(dj_id);

-- 8. ROW LEVEL SECURITY (RLS)
ALTER TABLE public.user_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_feed ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.playlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.playlist_tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tax_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dj_branding ENABLE ROW LEVEL SECURITY;

-- Basic RLS Policies (to be refined in Phase 2/3)
DO $$ BEGIN
    CREATE POLICY "Users can manage their own devices" ON public.user_devices FOR ALL USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE POLICY "Public can view comments" ON public.comments FOR SELECT USING (true);
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE POLICY "Users can comment" ON public.comments FOR INSERT WITH CHECK (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE POLICY "Public can view public playlists" ON public.playlists FOR SELECT USING (is_public = true OR auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN null; END $$;
-- 9. REMOTE REVOCATION & EXPIRY
ALTER TABLE public.tracks ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE public.tracks ADD COLUMN IF NOT EXISTS version_type TEXT DEFAULT 'original';
ALTER TABLE public.album_packs ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE public.purchases ADD COLUMN IF NOT EXISTS is_revoked BOOLEAN DEFAULT false;
ALTER TABLE public.dj_subscriptions ADD COLUMN IF NOT EXISTS is_revoked BOOLEAN DEFAULT false;

-- 10. USER MANAGEMENT
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT false;

-- 11. COMPLIANCE & REPORTS
CREATE TABLE IF NOT EXISTS public.copyright_reports (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    reporter_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE,
    album_id UUID REFERENCES public.album_packs(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    evidence_url TEXT,
    status TEXT DEFAULT 'pending' NOT NULL, -- 'pending', 'reviewed', 'actioned', 'rejected'
    admin_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 12. SUPPORT & ANNOUNCEMENTS
CREATE TABLE IF NOT EXISTS public.support_tickets (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    category TEXT NOT NULL, -- 'technical', 'billing', 'content', 'other'
    priority TEXT DEFAULT 'medium' NOT NULL, -- 'low', 'medium', 'high', 'urgent'
    status TEXT DEFAULT 'open' NOT NULL, -- 'open', 'in_progress', 'resolved', 'closed'
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.announcements (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    target_audience TEXT DEFAULT 'all' NOT NULL, -- 'all', 'djs', 'users'
    active BOOLEAN DEFAULT true,
    starts_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 13. OPERATIONAL
CREATE TABLE IF NOT EXISTS public.feature_flags (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_enabled BOOLEAN DEFAULT false,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);
