import { supabaseServer } from "./supabaseServer";
import { logger } from "./logger";
import crypto from "crypto";

/**
 * MixMint Content Moderation System
 * Detects duplicate uploads and potential copyright violations
 */

/**
 * generateFingerprint
 * Creates a perceptual hash of audio file for duplicate detection
 * Note: This is a simplified implementation. In production, use a library like chromaprint
 */
export function generateFingerprint(audioBuffer: Buffer): string {
    // Simplified fingerprint: hash of file chunks
    // In production, use proper audio fingerprinting (chromaprint, echoprint, etc.)
    const hash = crypto.createHash('sha256');
    
    // Sample chunks from different parts of the file
    const chunkSize = 4096;
    const numChunks = 10;
    const step = Math.floor(audioBuffer.length / numChunks);
    
    for (let i = 0; i < numChunks; i++) {
        const offset = i * step;
        const chunk = audioBuffer.slice(offset, offset + chunkSize);
        hash.update(chunk);
    }
    
    return hash.digest('hex');
}

/**
 * checkForDuplicates
 * Compares fingerprint against existing tracks
 */
export async function checkForDuplicates(
    fingerprint: string,
    trackId: string
): Promise<{ isDuplicate: boolean; matchedTrackId?: string; similarity?: number }> {
    try {
        // 1. Check for exact match
        const { data: exactMatch } = await supabaseServer
            .from('track_fingerprints')
            .select('track_id')
            .eq('fingerprint', fingerprint)
            .neq('track_id', trackId)
            .single();

        if (exactMatch) {
            return {
                isDuplicate: true,
                matchedTrackId: exactMatch.track_id,
                similarity: 100
            };
        }

        // 2. Check for similar fingerprints (Hamming distance)
        // Note: This is simplified. In production, use proper similarity algorithms
        const { data: allFingerprints } = await supabaseServer
            .from('track_fingerprints')
            .select('track_id, fingerprint')
            .neq('track_id', trackId)
            .limit(1000); // Limit for performance

        if (!allFingerprints) return { isDuplicate: false };

        for (const existing of allFingerprints) {
            const similarity = calculateSimilarity(fingerprint, existing.fingerprint);
            if (similarity > 90) {
                return {
                    isDuplicate: true,
                    matchedTrackId: existing.track_id,
                    similarity
                };
            }
        }

        return { isDuplicate: false };

    } catch (err) {
        logger.error("SYSTEM", "Duplicate check failed", err, { trackId });
        return { isDuplicate: false };
    }
}

/**
 * calculateSimilarity
 * Calculates similarity percentage between two fingerprints
 */
function calculateSimilarity(fp1: string, fp2: string): number {
    if (fp1.length !== fp2.length) return 0;
    
    let matches = 0;
    for (let i = 0; i < fp1.length; i++) {
        if (fp1[i] === fp2[i]) matches++;
    }
    
    return (matches / fp1.length) * 100;
}

/**
 * storeFingerprint
 * Saves fingerprint for a track
 */
export async function storeFingerprint(trackId: string, fingerprint: string) {
    try {
        await supabaseServer
            .from('track_fingerprints')
            .insert({
                track_id: trackId,
                fingerprint,
                algorithm: 'sha256_chunks'
            });
    } catch (err) {
        logger.error("SYSTEM", "Failed to store fingerprint", err, { trackId });
    }
}

/**
 * addToModerationQueue
 * Flags content for manual review
 */
export async function addToModerationQueue(
    trackId: string,
    reason: 'duplicate' | 'copyright' | 'metadata_suspicious' | 'manual_flag',
    similarityScore?: number,
    matchedTrackId?: string
) {
    try {
        await supabaseServer
            .from('moderation_queue')
            .insert({
                track_id: trackId,
                reason,
                similarity_score: similarityScore,
                matched_track_id: matchedTrackId,
                status: 'pending'
            });

        logger.warn("SYSTEM", `Track added to moderation queue: ${reason}`, {
            trackId,
            similarityScore,
            matchedTrackId
        });
    } catch (err) {
        logger.error("SYSTEM", "Failed to add to moderation queue", err, { trackId });
    }
}

/**
 * checkMetadataSuspicious
 * Detects suspicious patterns in track metadata
 */
export async function checkMetadataSuspicious(
    title: string,
    djId: string
): Promise<boolean> {
    try {
        // 1. Check for copyrighted artist names (simplified list)
        const copyrightedArtists = [
            'drake', 'beyonce', 'taylor swift', 'ed sheeran', 'ariana grande',
            'the weeknd', 'billie eilish', 'dua lipa', 'post malone'
        ];

        const titleLower = title.toLowerCase();
        const hasCopyrightedName = copyrightedArtists.some(artist => 
            titleLower.includes(artist)
        );

        if (hasCopyrightedName) return true;

        // 2. Check for bulk uploads from new accounts
        const { data: djProfile } = await supabaseServer
            .from('dj_profiles')
            .select('created_at')
            .eq('id', djId)
            .single();

        if (djProfile) {
            const accountAge = Date.now() - new Date(djProfile.created_at).getTime();
            const isNewAccount = accountAge < 7 * 24 * 60 * 60 * 1000; // 7 days

            if (isNewAccount) {
                const { count } = await supabaseServer
                    .from('tracks')
                    .select('*', { count: 'exact', head: true })
                    .eq('dj_id', djId)
                    .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString());

                if (count && count > 10) return true; // More than 10 tracks in 24h from new account
            }
        }

        return false;

    } catch (err) {
        logger.error("SYSTEM", "Metadata check failed", err, { title, djId });
        return false;
    }
}
