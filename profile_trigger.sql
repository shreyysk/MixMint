-- Supabase Automation: Profiles Trigger
-- This script ensures every signup in Supabase Auth creates a MixMint Profile.

-- 1. Function to handle new user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, role)
  VALUES (
    new.id,
    COALESCE(new.raw_user_meta_data->>'full_name', 'User'),
    'user'
  );
  
  -- Also initialize a wallet for the user
  INSERT INTO public.wallets (id, balance)
  VALUES (new.id, 0.00);

  -- Also initialize points for the user
  INSERT INTO public.points (id, balance)
  VALUES (new.id, 0);

  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Trigger to execute function on auth.users insert
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
