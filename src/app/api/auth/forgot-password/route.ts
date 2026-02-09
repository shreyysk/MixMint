
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

import { supabaseAdmin } from '@/lib/supabaseServer';

export async function POST(request: Request) {
  const requestUrl = new URL(request.url);
  const formData = await request.formData();
  const email = formData.get('email');

  if (typeof email !== 'string') {
    return NextResponse.redirect(
      `${requestUrl.origin}/auth/forgot-password?error=Email is required`,
      {
        // a 301 status is required to redirect from a POST to a GET route
        status: 301,
      }
    );
  }

  const supabase = createRouteHandlerClient({ cookies });

  // Check if user exists
  const { data: user, error: userError } = await supabaseAdmin
    .from('users')
    .select('id')
    .eq('email', email)
    .single();

  if (!user || userError) {
    return NextResponse.redirect(
      `${requestUrl.origin}/auth/forgot-password?error=No user registered with this email`,
      {
        status: 301,
      }
    );
  }

  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${requestUrl.origin}/auth/reset-password`,
  });

  if (error) {
    return NextResponse.redirect(
      `${requestUrl.origin}/auth/forgot-password?error=${error.message}`,
      {
        status: 301,
      }
    );
  }

  return NextResponse.redirect(
    `${requestUrl.origin}/auth/forgot-password?message=Password reset link sent to your email`,
    {
      status: 301,
    }
  );
}
