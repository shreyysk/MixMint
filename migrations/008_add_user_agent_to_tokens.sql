-- Add user_agent column to download_tokens table for device fingerprinting
ALTER TABLE public.download_tokens 
ADD COLUMN IF NOT EXISTS user_agent TEXT;
