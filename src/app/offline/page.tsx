'use client';

import { useEffect, useState } from 'react';
import { WifiOff, RefreshCw, Music } from 'lucide-react';
import { getCachedTracks } from '@/lib/offlineManager';
import type { TrackMetadata } from '@/lib/offlineManager';

export default function OfflinePage() {
    const [isOnline, setIsOnline] = useState(true);
    const [cachedTracks, setCachedTracks] = useState<TrackMetadata[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check online status
        setIsOnline(navigator.onLine);

        const handleOnline = () => setIsOnline(true);
        const handleOffline = () => setIsOnline(false);

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    useEffect(() => {
        loadCachedTracks();
    }, []);

    const loadCachedTracks = async () => {
        setLoading(true);
        try {
            const tracks = await getCachedTracks();
            setCachedTracks(tracks);
        } catch (error) {
            console.error('Error loading cached tracks:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleRetry = () => {
        if (navigator.onLine) {
            window.location.href = '/';
        } else {
            alert('Still offline. Please check your internet connection.');
        }
    };

    return (
        <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-6">
            <div className="max-w-md w-full text-center space-y-6">
                {/* Offline Icon */}
                <div className="flex justify-center">
                    <div className="w-24 h-24 rounded-full bg-purple-500/10 flex items-center justify-center">
                        <WifiOff className="w-12 h-12 text-purple-400" />
                    </div>
                </div>

                {/* Status */}
                <div>
                    <h1 className="text-3xl font-bold mb-2">
                        {isOnline ? 'Back Online!' : 'You\'re Offline'}
                    </h1>
                    <p className="text-gray-400">
                        {isOnline
                            ? 'Your connection has been restored.'
                            : 'No internet connection. You can still access your cached tracks below.'
                        }
                    </p>
                </div>

                {/* Retry Button */}
                {isOnline && (
                    <button
                        onClick={handleRetry}
                        className="w-full px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                    >
                        <RefreshCw className="w-5 h-5" />
                        Return to MixMint
                    </button>
                )}

                {/* Cached Tracks */}
                {!loading && cachedTracks.length > 0 && (
                    <div className="mt-8 text-left">
                        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                            <Music className="w-5 h-5 text-purple-400" />
                            Cached Tracks ({cachedTracks.length})
                        </h2>
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                            {cachedTracks.map((track) => (
                                <div
                                    key={track.id}
                                    className="p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors"
                                >
                                    <div className="font-medium">{track.title}</div>
                                    <div className="text-sm text-gray-400">{track.artist}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {!loading && cachedTracks.length === 0 && !isOnline && (
                    <div className="mt-8 p-4 bg-white/5 rounded-lg">
                        <p className="text-gray-400 text-sm">
                            No tracks cached for offline playback. When online, you can cache tracks from your library.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
