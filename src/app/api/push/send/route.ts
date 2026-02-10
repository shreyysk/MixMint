import { NextRequest, NextResponse } from 'next/server';
import { supabaseServer } from '@/lib/supabaseServer';
import webpush from 'web-push';

interface PushSubscription {
  id: string;
  user_id: string;
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
}

// Configure web-push with VAPID keys
if (process.env.VAPID_PUBLIC_KEY && process.env.VAPID_PRIVATE_KEY) {
  webpush.setVapidDetails(
    'mailto:support@mixmint.com',
    process.env.VAPID_PUBLIC_KEY,
    process.env.VAPID_PRIVATE_KEY
  );
}

export async function POST(request: NextRequest) {
  try {
    const supabase = supabaseServer;
    
    // Check authentication and admin role
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Verify admin role
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single();

    if (profile?.role !== 'admin') {
      return NextResponse.json(
        { error: 'Forbidden - Admin access required' },
        { status: 403 }
      );
    }

    const body = await request.json();
    const { 
      title, 
      message, 
      url, 
      userIds, // Optional: specific user IDs to send to
      tag 
    } = body;

    if (!title || !message) {
      return NextResponse.json(
        { error: 'Title and message are required' },
        { status: 400 }
      );
    }

    // Get push subscriptions
    let query = supabase
      .from('push_subscriptions')
      .select('*');

    if (userIds && userIds.length > 0) {
      query = query.in('user_id', userIds);
    }

    const { data: subscriptions, error: fetchError } = await query;

    if (fetchError) {
      console.error('[Push Send] Database error:', fetchError);
      return NextResponse.json(
        { error: 'Failed to fetch subscriptions' },
        { status: 500 }
      );
    }

    if (!subscriptions || subscriptions.length === 0) {
      return NextResponse.json(
        { message: 'No subscriptions found', sent: 0 },
        { status: 200 }
      );
    }

    // Prepare notification payload
    const payload = JSON.stringify({
      title,
      body: message,
      url: url || '/',
      tag: tag || 'default',
      icon: '/icons/icon-192x192.png',
      badge: '/icons/icon-72x72.png'
    });

    // Send notifications
    const results = await Promise.allSettled(
      subscriptions.map(async (sub: PushSubscription) => {
        try {
          const pushSubscription = {
            endpoint: sub.endpoint,
            keys: sub.keys
          };

          await webpush.sendNotification(pushSubscription, payload);
          return { success: true, userId: sub.user_id };
        } catch (error: unknown) {
          const pushError = error as { statusCode?: number; message?: string };
          console.error(`[Push Send] Failed for user ${sub.user_id}:`, pushError);
          
          // Remove invalid subscriptions (410 Gone)
          if (pushError.statusCode === 410) {
            await supabase
              .from('push_subscriptions')
              .delete()
              .eq('id', sub.id);
          }
          
          return { success: false, userId: sub.user_id, error: pushError.message || 'Unknown error' };
        }
      })
    );

    const successful = results.filter((r): r is PromiseFulfilledResult<{ success: boolean; userId: string }> => 
      r.status === 'fulfilled' && r.value.success
    ).length;
    const failed = results.length - successful;

    return NextResponse.json({
      message: 'Notifications sent',
      sent: successful,
      failed,
      total: results.length
    });
  } catch (error) {
    console.error('[Push Send] Error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
