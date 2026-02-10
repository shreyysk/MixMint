-- Add cover_url to tracks table for storing album art
ALTER TABLE public.tracks 
ADD COLUMN IF NOT EXISTS cover_url TEXT;

-- Add cover_url to album_packs table as well if missing (just in case)
ALTER TABLE public.album_packs
ADD COLUMN IF NOT EXISTS cover_url TEXT;
