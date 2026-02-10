/**
 * Offline Manager for MixMint PWA
 * Handles caching tracks for offline playback
 */

export interface TrackMetadata {
  id: string;
  title: string;
  artist: string;
  coverUrl?: string;
  audioUrl: string;
  cached: boolean;
  cachedAt?: number;
}

const DB_NAME = 'mixmint-offline';
const DB_VERSION = 1;
const STORE_NAME = 'tracks';
const CACHE_NAME = 'mixmint-tracks';

/**
 * Open IndexedDB database
 */
async function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
        store.createIndex('cached', 'cached', { unique: false });
        store.createIndex('cachedAt', 'cachedAt', { unique: false });
      }
    };
  });
}

/**
 * Cache a track for offline playback
 */
export async function cacheTrackForOffline(
  trackId: string,
  audioUrl: string,
  metadata: Omit<TrackMetadata, 'id' | 'cached' | 'cachedAt'>
): Promise<boolean> {
  try {
    // 1. Cache audio file in Cache API
    const cache = await caches.open(CACHE_NAME);
    await cache.add(audioUrl);

    // 2. Store metadata in IndexedDB
    const db = await openDB();
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);

    const trackData: TrackMetadata = {
      id: trackId,
      ...metadata,
      audioUrl,
      cached: true,
      cachedAt: Date.now()
    };

    await new Promise((resolve, reject) => {
      const request = store.put(trackData);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });

    // 3. Update server
    await fetch('/api/offline/cache', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trackId, cached: true })
    });

    console.log(`[Offline] Successfully cached track ${trackId}`);
    return true;
  } catch (error) {
    console.error('[Offline] Error caching track:', error);
    return false;
  }
}

/**
 * Remove a track from offline cache
 */
export async function removeCachedTrack(trackId: string): Promise<boolean> {
  try {
    // 1. Get track metadata
    const db = await openDB();
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);

    const track = await new Promise<TrackMetadata>((resolve, reject) => {
      const request = store.get(trackId);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });

    if (!track) {
      return true; // Already removed
    }

    // 2. Remove from Cache API
    const cache = await caches.open(CACHE_NAME);
    await cache.delete(track.audioUrl);

    // 3. Remove from IndexedDB
    const deleteTransaction = db.transaction([STORE_NAME], 'readwrite');
    const deleteStore = deleteTransaction.objectStore(STORE_NAME);

    await new Promise((resolve, reject) => {
      const request = deleteStore.delete(trackId);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });

    // 4. Update server
    await fetch('/api/offline/cache', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trackId, cached: false })
    });

    console.log(`[Offline] Successfully removed cached track ${trackId}`);
    return true;
  } catch (error) {
    console.error('[Offline] Error removing cached track:', error);
    return false;
  }
}

/**
 * Get all cached tracks
 */
export async function getCachedTracks(): Promise<TrackMetadata[]> {
  try {
    const db = await openDB();
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);
    const index = store.index('cached');

    return new Promise((resolve, reject) => {
      const request = store.getAll(); // Get all tracks
      request.onsuccess = () => {
        // Filter for cached tracks
        const cachedTracks = (request.result as TrackMetadata[]).filter(t => t.cached);
        resolve(cachedTracks);
      };
      request.onerror = () => reject(request.error);
    });
  } catch (error) {
    console.error('[Offline] Error getting cached tracks:', error);
    return [];
  }
}

/**
 * Check if a track is cached
 */
export async function isTrackCached(trackId: string): Promise<boolean> {
  try {
    const db = await openDB();
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);

    const track = await new Promise<TrackMetadata>((resolve, reject) => {
      const request = store.get(trackId);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });

    return track?.cached || false;
  } catch (error) {
    console.error('[Offline] Error checking if track is cached:', error);
    return false;
  }
}

/**
 * Get total cache size
 */
export async function getCacheSize(): Promise<number> {
  try {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate();
      return estimate.usage || 0;
    }
    return 0;
  } catch (error) {
    console.error('[Offline] Error getting cache size:', error);
    return 0;
  }
}

/**
 * Clear all offline cache
 */
export async function clearOfflineCache(): Promise<boolean> {
  try {
    // 1. Clear Cache API
    await caches.delete(CACHE_NAME);

    // 2. Clear IndexedDB
    const db = await openDB();
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);

    await new Promise((resolve, reject) => {
      const request = store.clear();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });

    console.log('[Offline] Successfully cleared all offline cache');
    return true;
  } catch (error) {
    console.error('[Offline] Error clearing offline cache:', error);
    return false;
  }
}
