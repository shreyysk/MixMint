import { supabaseServer } from "@/lib/supabaseServer";
import { ok, fail } from "@/lib/apiResponse";

/**
 * Cron job to check wishlist price changes and send notifications
 * Should run daily via Vercel Cron or similar
 */
export async function GET(req: Request) {
  try {
    // Verify cron secret
    const authHeader = req.headers.get("authorization");
    if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
      return fail("Unauthorized", 401);
    }

    // 1. Get all tracks with price changes in last 24 hours
    const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

    const { data: tracks } = await supabaseServer
      .from("tracks")
      .select("id, title, price, updated_at")
      .gte("updated_at", yesterday);

    if (!tracks || tracks.length === 0) {
      return ok({ message: "No price changes detected", notificationsSent: 0 });
    }

    let notificationsSent = 0;

    for (const track of tracks) {
      // 2. Check if price actually changed
      const { data: priceHistory } = await supabaseServer
        .from("wishlist_price_history")
        .select("price")
        .eq("track_id", track.id)
        .order("recorded_at", { ascending: false })
        .limit(2);

      if (!priceHistory || priceHistory.length < 2) {
        // Record current price for future comparison
        await supabaseServer
          .from("wishlist_price_history")
          .insert({
            track_id: track.id,
            price: track.price
          });
        continue;
      }

      const previousPrice = priceHistory[1].price;
      const currentPrice = track.price;

      // Skip if no change
      if (previousPrice === currentPrice) continue;

      const isPriceDrop = currentPrice < previousPrice;
      const isFree = currentPrice === 0;

      // 3. Find users who wishlisted this track
      const { data: wishlisters } = await supabaseServer
        .from("wishlist")
        .select(`
          user_id,
          profiles (
            email,
            full_name,
            notification_preferences
          )
        `)
        .eq("track_id", track.id);

      if (!wishlisters) continue;

      // 4. Send notifications to eligible users
      for (const item of wishlisters) {
        const prefs = (item.profiles as any)?.notification_preferences || {};
        
        // Check notification preferences
        if (isFree && !prefs.wishlist_free) continue;
        if (isPriceDrop && !isFree && !prefs.wishlist_price_drop) continue;

        // TODO: Send email notification via Resend
        // For now, just log
        console.log(`[WISHLIST_NOTIFICATION] User ${item.user_id} - Track ${track.title} - ${isFree ? 'Now Free!' : `Price drop: ₹${previousPrice} → ₹${currentPrice}`}`);
        
        notificationsSent++;
      }

      // 5. Record new price
      await supabaseServer
        .from("wishlist_price_history")
        .insert({
          track_id: track.id,
          price: currentPrice
        });
    }

    return ok({ 
      message: "Wishlist notifications processed",
      tracksChecked: tracks.length,
      notificationsSent
    });

  } catch (err: any) {
    console.error("[WISHLIST_NOTIFICATIONS_ERROR]:", err);
    return fail(err.message || "Internal error", 500);
  }
}
