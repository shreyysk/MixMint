-- Migration 015: Advanced Analytics & Referral Tiering
-- Phase 17 Implementation

-- 1. Extend Purchases for Analytics
ALTER TABLE public.purchases 
ADD COLUMN IF NOT EXISTS seller_id UUID REFERENCES public.dj_profiles(id),
ADD COLUMN IF NOT EXISTS price_paid DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS dj_earnings DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS ip_address INET,
ADD COLUMN IF NOT EXISTS location_data JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS user_agent TEXT;

-- Populate seller_id for existing records
UPDATE public.purchases p
SET seller_id = COALESCE(
    (SELECT dj_id FROM public.tracks t WHERE t.id = p.content_id),
    (SELECT dj_id FROM public.album_packs a WHERE a.id = p.content_id),
    (SELECT dj_id FROM public.albums al WHERE al.id = p.content_id) -- Handle 'albums' table if it exists
)
WHERE seller_id IS NULL;

-- Backfill price_paid if amount or price exists
DO $$ 
BEGIN 
    -- Check for 'amount' column
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='purchases' AND column_name='amount') THEN
        UPDATE public.purchases SET price_paid = amount WHERE price_paid IS NULL;
    END IF;
    
    -- Check for 'price' column (from user's JSON)
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='purchases' AND column_name='price') THEN
        -- If price is integer (cents), divide by 100. If it's already decimal, just use it.
        UPDATE public.purchases 
        SET price_paid = CASE 
            WHEN (SELECT data_type FROM information_schema.columns WHERE table_name='purchases' AND column_name='price') = 'integer' 
            THEN price::decimal / 100 
            ELSE price::decimal 
        END
        WHERE price_paid IS NULL;
    END IF;

    -- Estimate dj_earnings (default 88%)
    UPDATE public.purchases SET dj_earnings = price_paid * 0.88 WHERE dj_earnings IS NULL AND price_paid IS NOT NULL;
END $$;

-- 2. Extend DJ Referral Tiers
-- Track referral level for tiered rewards (e.g. Bronze, Silver, Gold referrers)
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS referral_tier TEXT DEFAULT 'bronze' CHECK (referral_tier IN ('bronze', 'silver', 'gold', 'platinum'));

-- 3. Analytics Views for DJs
-- Use dynamic SQL (EXECUTE) to prevent parse-time errors in the Supabase editor
DO $$
BEGIN
    EXECUTE 'CREATE OR REPLACE VIEW public.dj_sale_analytics AS
    SELECT 
        seller_id as dj_id,
        content_type,
        COUNT(id) as total_sales,
        SUM(price_paid) as gross_revenue,
        SUM(dj_earnings) as net_earnings,
        location_data->>''country'' as country,
        location_data->>''city'' as city,
        DATE_TRUNC(''day'', created_at) as sale_date
    FROM public.purchases
    GROUP BY seller_id, content_type, country, city, sale_date;';
    
    -- Enable RLS for the view
    EXECUTE 'ALTER VIEW public.dj_sale_analytics SET (security_invoker = on);';
END $$;

-- 4. Referral Tier logic trigger (Optional: for later automation)
-- This could be a cron or a trigger that promotes users based on successful verified referrals
