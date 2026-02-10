import { supabaseServer } from "./supabaseServer";
import { logger } from "./logger";

/**
 * MixMint Smart Recommendations Engine
 * Hybrid approach: Collaborative Filtering + Content-Based Filtering
 */

interface TrackRecommendation {
    track_id: string;
    title: string;
    dj_name: string;
    price: number;
    genre: string;
    score: number;
    reason: string;
}

/**
 * getRecommendations
 * Returns personalized track recommendations for a user
 */
export async function getRecommendations(
    userId: string,
    limit: number = 10
): Promise<TrackRecommendation[]> {
    try {
        // 1. Get user's purchase history and interactions
        const { data: userHistory } = await supabaseServer
            .from('user_interactions')
            .select('track_id, interaction_type')
            .eq('user_id', userId)
            .in('interaction_type', ['purchase', 'wishlist', 'play']);

        const purchasedTrackIds = userHistory?.map(h => h.track_id) || [];

        // 2. Get user's followed DJs
        const { data: followedDJs } = await supabaseServer
            .from('follows')
            .select('followed_id')
            .eq('follower_id', userId);

        const followedDJIds = followedDJs?.map(f => f.followed_id) || [];

        // 3. Collaborative Filtering: Find similar users
        const collaborativeRecs = await getCollaborativeRecommendations(
            userId,
            purchasedTrackIds,
            limit
        );

        // 4. Content-Based: Recommend from followed DJs
        const contentBasedRecs = await getContentBasedRecommendations(
            followedDJIds,
            purchasedTrackIds,
            limit
        );

        // 5. Merge and deduplicate
        const allRecs = [...collaborativeRecs, ...contentBasedRecs];
        const uniqueRecs = deduplicateRecommendations(allRecs);

        // 6. Sort by score and return top N
        return uniqueRecs
            .sort((a, b) => b.score - a.score)
            .slice(0, limit);

    } catch (err) {
        logger.error("SYSTEM", "Failed to generate recommendations", err, { userId });
        return [];
    }
}

/**
 * Collaborative Filtering: "Users who bought X also bought Y"
 */
async function getCollaborativeRecommendations(
    userId: string,
    purchasedTrackIds: string[],
    limit: number
): Promise<TrackRecommendation[]> {
    if (purchasedTrackIds.length === 0) return [];

    // Find users with similar purchase patterns
    const { data: similarUsers } = await supabaseServer
        .from('user_interactions')
        .select('user_id')
        .in('track_id', purchasedTrackIds)
        .eq('interaction_type', 'purchase')
        .neq('user_id', userId);

    if (!similarUsers || similarUsers.length === 0) return [];

    const similarUserIds = [...new Set(similarUsers.map(u => u.user_id))];

    // Get tracks purchased by similar users
    const { data: recommendations } = await supabaseServer
        .from('user_interactions')
        .select(`
            track_id,
            tracks (
                id,
                title,
                price,
                genre,
                dj_profiles (dj_name)
            )
        `)
        .in('user_id', similarUserIds)
        .eq('interaction_type', 'purchase')
        .not('track_id', 'in', `(${purchasedTrackIds.join(',')})`)
        .limit(limit * 2);

    if (!recommendations) return [];

    // Calculate scores based on frequency
    const trackScores = new Map<string, number>();
    recommendations.forEach(rec => {
        const count = trackScores.get(rec.track_id) || 0;
        trackScores.set(rec.track_id, count + 1);
    });

    return recommendations
        .filter(rec => rec.tracks)
        .map(rec => ({
            track_id: rec.track_id,
            title: (rec.tracks as any).title,
            dj_name: (rec.tracks as any).dj_profiles?.dj_name || 'Unknown',
            price: (rec.tracks as any).price,
            genre: (rec.tracks as any).genre,
            score: trackScores.get(rec.track_id) || 1,
            reason: 'Users with similar taste also bought this'
        }));
}

/**
 * Content-Based: Recommend from followed DJs and similar genres
 */
async function getContentBasedRecommendations(
    followedDJIds: string[],
    purchasedTrackIds: string[],
    limit: number
): Promise<TrackRecommendation[]> {
    if (followedDJIds.length === 0) return [];

    const { data: tracks } = await supabaseServer
        .from('tracks')
        .select(`
            id,
            title,
            price,
            genre,
            dj_profiles (dj_name)
        `)
        .in('dj_id', followedDJIds)
        .not('id', 'in', `(${purchasedTrackIds.join(',')})`)
        .order('created_at', { ascending: false })
        .limit(limit);

    if (!tracks) return [];

    return tracks.map(track => ({
        track_id: track.id,
        title: track.title,
        dj_name: (track.dj_profiles as any)?.dj_name || 'Unknown',
        price: track.price,
        genre: track.genre || '',
        score: 0.8, // Lower score than collaborative
        reason: 'New from DJs you follow'
    }));
}

/**
 * Deduplicate recommendations by track_id
 */
function deduplicateRecommendations(
    recs: TrackRecommendation[]
): TrackRecommendation[] {
    const seen = new Set<string>();
    return recs.filter(rec => {
        if (seen.has(rec.track_id)) return false;
        seen.add(rec.track_id);
        return true;
    });
}

/**
 * trackInteraction
 * Log user interaction for future recommendations
 */
export async function trackInteraction(
    userId: string,
    trackId: string | null,
    djId: string | null,
    interactionType: 'view' | 'purchase' | 'wishlist' | 'follow_dj' | 'play'
) {
    try {
        await supabaseServer
            .from('user_interactions')
            .insert({
                user_id: userId,
                track_id: trackId,
                dj_id: djId,
                interaction_type: interactionType
            });
    } catch (err) {
        logger.warn("SYSTEM", "Failed to track interaction", { userId, trackId, interactionType });
    }
}
