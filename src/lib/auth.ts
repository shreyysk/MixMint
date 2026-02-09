import { supabase } from "./supabaseClient";

export async function signUp(email: string, password: string, fullName: string) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: fullName,
      },
    },
  });

  if (error) throw error;

  // Track referral if session exists (triggers handle profile/wallet/points)
  if (data.session) {
    const ref = typeof window !== 'undefined' ? localStorage.getItem('mixmint_ref') : null;
    if (ref) {
      try {
        await fetch('/api/rewards/track', {
          method: 'POST',
          body: JSON.stringify({ referralCode: ref }),
          headers: { 'Content-Type': 'application/json' }
        });
        localStorage.removeItem('mixmint_ref');
      } catch (e) {
        console.warn("Points tracking failed. Will retry on next login.", e);
      }
    }
  }

  return data;
}

export async function signIn(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) throw error;

  return data;
}

export async function signOut() {
  await supabase.auth.signOut();
}
