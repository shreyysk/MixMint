-- ============================================
-- MixMint Album/ZIP Processing Schema
-- ============================================
-- Phase 13: Advanced Album Management
-- ============================================

-- 1. Update album_packs with processing fields
ALTER TABLE public.album_packs 
ADD COLUMN IF NOT EXISTS upload_method TEXT CHECK (upload_method IN ('system_generated', 'direct_zip')) DEFAULT 'direct_zip',
ADD COLUMN IF NOT EXISTS original_file_key TEXT, -- Storage key for original upload
ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'queued')),
ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS processing_completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS processing_error TEXT,
ADD COLUMN IF NOT EXISTS track_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_duration INTEGER; -- in seconds

-- 2. Create album_tracks table (for system-generated ZIPs and tracking metadata)
CREATE TABLE IF NOT EXISTS public.album_tracks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    album_id UUID REFERENCES public.album_packs(id) ON DELETE CASCADE NOT NULL,
    track_order INTEGER NOT NULL,
    
    -- Original uploaded track (if system_generated)
    title TEXT NOT NULL,
    original_file_key TEXT, -- temp/ tracks storage
    processed_filename TEXT, -- name inside the ZIP
    
    -- Metadata
    duration INTEGER, -- seconds
    file_size BIGINT,
    format TEXT DEFAULT 'mp3',
    
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 3. Create processing queue tracker (optional but good for visibility)
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

-- Enable RLS
ALTER TABLE public.album_tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.album_processing_queue ENABLE ROW LEVEL SECURITY;

-- DJ access policies
CREATE POLICY "DJs can manage their own album tracks" ON public.album_tracks
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.album_packs WHERE id = album_tracks.album_id AND dj_id = auth.uid()));

CREATE POLICY "DJs can view their own processing queue" ON public.album_processing_queue
    FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.album_packs WHERE id = album_processing_queue.album_id AND dj_id = auth.uid()));

-- Indexing
CREATE INDEX IF NOT EXISTS idx_album_tracks_album ON public.album_tracks(album_id);
CREATE INDEX IF NOT EXISTS idx_album_processing_status ON public.album_packs(processing_status);
