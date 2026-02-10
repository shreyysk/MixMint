/**
 * Utility for YouTube and Instagram URL validation and ID extraction.
 */

export function extractYouTubeId(url: string): string | null {
  const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/i;
  const match = url.match(regex);
  return match ? match[1] : null;
}

export function extractInstagramId(url: string): string | null {
  // Accept: instagram.com/reel/REEL_ID/, instagram.com/p/POST_ID/, instagram.com/reels/REEL_ID/
  const regex = /(?:instagram\.com\/(?:reel|reels|p)\/)([^/?#\s]+)/i;
  const match = url.match(regex);
  return match ? match[1] : null;
}

export function validatePreviewUrl(url: string): { type: 'youtube' | 'instagram' | null; id: string | null } {
  if (!url) return { type: null, id: null };
  
  const ytId = extractYouTubeId(url);
  if (ytId) return { type: 'youtube', id: ytId };
  
  const igId = extractInstagramId(url);
  if (igId) return { type: 'instagram', id: igId };
  
  return { type: null, id: null };
}
