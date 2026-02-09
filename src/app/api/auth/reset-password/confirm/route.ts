
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const requestUrl = new URL(request.url);
  const formData = await request.formData();
  const password = formData.get('password');

  if (typeof password !== 'string' || password.length < 6) {
    return NextResponse.redirect(
      `${requestUrl.origin}/auth/reset-password?error=Password must be at least 6 characters`,
      {
        // a 301 status is required to redirect from a POST to a GET route
        status: 301,
      }
    );
  }

  const supabase = createRouteHandlerClient({ cookies });

  const { error } = await supabase.auth.updateUser({ password });

  if (error) {
    return NextResponse.redirect(
      `${requestUrl.origin}/auth/reset-password?error=${error.message}`,
      {
        status: 301,
      }
    );
  }

  return NextResponse.redirect(
    `${requestUrl.origin}/?message=Password updated successfully. You can now log in.`,
    {
      status: 301,
    }
  );
}
