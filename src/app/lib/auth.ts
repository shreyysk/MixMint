import { supabase } from "./supabaseClient";

export async function signUp(email: string, password: string, fullName: string) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
  });

  if (error) throw error;

  if (data.user) {
    await supabase.from("profiles").insert({
      id: data.user.id,
      full_name: fullName,
      role: "user",
    });

    // Track referral and award signup bonus if signed in automatically
    if (data.session) {
      const ref = localStorage.getItem('mixmint_ref');
      try {
        await fetch('/api/rewards/track', {
          method: 'POST',
          body: JSON.stringify({ referralCode: ref }),
          headers: { 'Content-Type': 'application/json' }
        });
        if (ref) localStorage.removeItem('mixmint_ref');
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
