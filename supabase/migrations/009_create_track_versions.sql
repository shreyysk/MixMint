-- MixMint Phase 5: Multiple Audio Formats
-- Create a table to store alternate versions of tracks (WAV, AIFF, FLAC, etc.)

DO $$ BEGIN
    CREATE TYPE audio_format AS ENUM ('mp3_320', 'wav', 'aiff', 'flac');
EXCEPTION WHEN duplicate_object THEN null; END $$;

CREATE TABLE IF NOT EXISTS public.track_versions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    track_id UUID REFERENCES public.tracks(id) ON DELETE CASCADE NOT NULL,
    format audio_format NOT NULL,
    file_key TEXT NOT NULL,
    file_size BIGINT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(track_id, format) -- Only one version per format per track
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_track_versions_track ON public.track_versions(track_id);

-- Add version_id to download_tokens to support specific version downloads
ALTER TABLE public.download_tokens 
ADD COLUMN IF NOT EXISTS version_id UUID REFERENCES public.track_versions(id) ON DELETE SET NULL;
