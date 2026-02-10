-- Migration 016: Phase 18 - Platform Intelligence & Automation
-- Smart Recommendations, Fraud Detection, Performance Monitoring, Content Moderation

-- 1. USER INTERACTIONS (for Recommendations Engine)
CREATE TABLE IF NOT EXISTS public.user_interactions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE,
    dj_id UUID REFERENCES public.dj_profiles(id) ON DELETE CASCADE,
    interaction_type TEXT NOT NULL CHECK (interaction_type IN ('view', 'purchase', 'wishlist', 'follow_dj', 'play')),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_interactions_user ON public.user_interactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_interactions_track ON public.user_interactions(track_id);
CREATE INDEX IF NOT EXISTS idx_user_interactions_type ON public.user_interactions(interaction_type);

-- 2. DJ ONBOARDING PROGRESS
CREATE TABLE IF NOT EXISTS public.dj_onboarding_progress (
    dj_id UUID PRIMARY KEY REFERENCES public.dj_profiles(id) ON DELETE CASCADE,
    steps_completed JSONB DEFAULT '[]'::jsonb, -- Array of completed step IDs
    email_sequence_stage INTEGER DEFAULT 0, -- Current email in sequence
    last_email_sent_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 3. FRAUD DETECTION
CREATE TABLE IF NOT EXISTS public.fraud_alerts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('referral_abuse', 'download_farming', 'payment_fraud', 'suspicious_activity')),
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    details JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'actioned', 'dismissed')),
    reviewed_by UUID REFERENCES public.profiles(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fraud_alerts_status ON public.fraud_alerts(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_user ON public.fraud_alerts(user_id);

-- 4. PERFORMANCE MONITORING
CREATE TABLE IF NOT EXISTS public.api_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    response_time_ms INTEGER NOT NULL,
    status_code INTEGER NOT NULL,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    ip_address INET,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Partition by day for performance (optional, can be added later)
CREATE INDEX IF NOT EXISTS idx_api_metrics_endpoint ON public.api_metrics(endpoint, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_metrics_slow_queries ON public.api_metrics(response_time_ms DESC) WHERE response_time_ms > 1000;

-- 5. CONTENT MODERATION (Audio Fingerprinting)
CREATE TABLE IF NOT EXISTS public.track_fingerprints (
    track_id UUID PRIMARY KEY REFERENCES public.tracks(id) ON DELETE CASCADE,
    fingerprint TEXT NOT NULL,
    algorithm TEXT DEFAULT 'chromaprint', -- fingerprinting algorithm used
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_track_fingerprints_hash ON public.track_fingerprints(fingerprint);

CREATE TABLE IF NOT EXISTS public.moderation_queue (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('duplicate', 'copyright', 'metadata_suspicious', 'manual_flag')),
    similarity_score DECIMAL(5,2),
    matched_track_id UUID REFERENCES public.tracks(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by UUID REFERENCES public.profiles(id),
    reviewed_at TIMESTAMPTZ,
    admin_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_moderation_queue_status ON public.moderation_queue(status, created_at DESC);

-- 6. RLS POLICIES
ALTER TABLE public.user_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dj_onboarding_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fraud_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.track_fingerprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.moderation_queue ENABLE ROW LEVEL SECURITY;

-- User Interactions: Users can see their own, admins can see all
DROP POLICY IF EXISTS "Users can view own interactions" ON public.user_interactions;
CREATE POLICY "Users can view own interactions" ON public.user_interactions
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own interactions" ON public.user_interactions;
CREATE POLICY "Users can insert own interactions" ON public.user_interactions
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- DJ Onboarding: DJs can see their own progress
DROP POLICY IF EXISTS "DJs can view own onboarding" ON public.dj_onboarding_progress;
CREATE POLICY "DJs can view own onboarding" ON public.dj_onboarding_progress
    FOR SELECT TO authenticated
    USING (auth.uid() = dj_id);

-- Fraud Alerts: Admin only
DROP POLICY IF EXISTS "Admins can manage fraud alerts" ON public.fraud_alerts;
CREATE POLICY "Admins can manage fraud alerts" ON public.fraud_alerts
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));

-- API Metrics: Admin only
DROP POLICY IF EXISTS "Admins can view metrics" ON public.api_metrics;
CREATE POLICY "Admins can view metrics" ON public.api_metrics
    FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));

-- Moderation Queue: Admin only
DROP POLICY IF EXISTS "Admins can manage moderation queue" ON public.moderation_queue;
CREATE POLICY "Admins can manage moderation queue" ON public.moderation_queue
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));
