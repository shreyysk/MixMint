-- Migration 013: A/B Testing & Experiments
-- Description: Adds infrastructure for platform experiments and variant tracking.

CREATE TABLE IF NOT EXISTS public.experiments (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'concluded')) NOT NULL,
    conversion_goal TEXT NOT NULL, -- e.g., 'signup', 'purchase', 'subscription'
    config JSONB DEFAULT '{}'::jsonb, -- Store variant details (e.g., button colors, text)
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Variant exposure tracking (Who saw what?)
CREATE TABLE IF NOT EXISTS public.experiment_exposures (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    experiment_id UUID REFERENCES public.experiments(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    variant_name TEXT NOT NULL, -- 'control', 'variant_a', etc.
    ip_address INET,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- RLS for Experiments
ALTER TABLE public.experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.experiment_exposures ENABLE ROW LEVEL SECURITY;

-- Admins can manage experiments
CREATE POLICY "Admins have full access to experiments" 
ON public.experiments FOR ALL 
TO authenticated 
USING (public.is_admin());

-- Public (anonymous or auth) can view running experiments to check variant
CREATE POLICY "Public can view running experiments" 
ON public.experiments FOR SELECT 
USING (status = 'running');

-- Users can record their own exposures
CREATE POLICY "Anyone can record exposures" 
ON public.experiment_exposures FOR INSERT 
WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_experiments_status ON public.experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiment_exposures_exp_user ON public.experiment_exposures(experiment_id, user_id);
