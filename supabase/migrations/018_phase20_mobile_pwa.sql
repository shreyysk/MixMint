-- Migration 018: Phase 20 - Mobile & PWA
-- Push Subscriptions for browser notifications

CREATE TABLE IF NOT EXISTS public.push_subscriptions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    endpoint TEXT NOT NULL,
    keys JSONB NOT NULL, -- {p256dh, auth}
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    last_used TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(user_id, endpoint)
);

CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user ON public.push_subscriptions(user_id);

-- Add offline caching flag to purchases
ALTER TABLE public.purchases
ADD COLUMN IF NOT EXISTS cached_offline BOOLEAN DEFAULT false;

-- RLS Policies
ALTER TABLE public.push_subscriptions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage own push subscriptions" ON public.push_subscriptions;
CREATE POLICY "Users can manage own push subscriptions" ON public.push_subscriptions
    FOR ALL TO authenticated
    USING (auth.uid() = user_id);
