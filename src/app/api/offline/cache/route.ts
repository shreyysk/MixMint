import { NextRequest, NextResponse } from 'next/server';
import { supabaseServer } from '@/lib/supabaseServer';

export async function POST(request: NextRequest) {
  try {
    const supabase = supabaseServer;
    
    // Check authentication
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { trackId, cached } = body;

    if (!trackId || typeof cached !== 'boolean') {
      return NextResponse.json(
        { error: 'Invalid request data' },
        { status: 400 }
      );
    }

    // Verify user owns this track
    const { data: purchase } = await supabase
      .from('purchases')
      .select('id')
      .eq('user_id', user.id)
      .eq('track_id', trackId)
      .single();

    if (!purchase) {
      return NextResponse.json(
        { error: 'Track not found in your purchases' },
        { status: 404 }
      );
    }

    // Update cached status
    const { error: updateError } = await supabase
      .from('purchases')
      .update({ cached_offline: cached })
      .eq('user_id', user.id)
      .eq('track_id', trackId);

    if (updateError) {
      console.error('[Offline Cache] Database error:', updateError);
      return NextResponse.json(
        { error: 'Failed to update cache status' },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('[Offline Cache] Error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
