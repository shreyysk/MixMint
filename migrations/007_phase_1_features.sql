-- 007_phase_1_features.sql

-- 1. Track Previews Table
ALTER TABLE public.tracks DROP COLUMN IF EXISTS youtube_url;

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

-- 2. Follows Table
CREATE TABLE IF NOT EXISTS public.follows (
    follower_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    followed_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (follower_id, followed_id)
);

-- 3. Wishlists Table
CREATE TABLE IF NOT EXISTS public.wishlists (
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    content_id UUID NOT NULL, 
    content_type content_type NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (user_id, content_id, content_type)
);

-- 4. Reviews Table
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

-- 5. Additional Discovery Fields
ALTER TABLE public.dj_profiles ADD COLUMN IF NOT EXISTS location TEXT;
ALTER TABLE public.dj_profiles ADD COLUMN IF NOT EXISTS popularity_score INT DEFAULT 0;
ALTER TABLE public.dj_profiles ADD COLUMN IF NOT EXISTS genres TEXT[]; -- Array of genres (e.g. ['House', 'Techno'])

-- 6. Indexes
CREATE INDEX IF NOT EXISTS idx_track_previews_track ON public.track_previews(track_id);
CREATE INDEX IF NOT EXISTS idx_follows_followed ON public.follows(followed_id);
CREATE INDEX IF NOT EXISTS idx_wishlists_user ON public.wishlists(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_track ON public.reviews(track_id);
