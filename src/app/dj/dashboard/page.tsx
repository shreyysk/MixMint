"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/app/lib/AuthContext";
import { supabase } from "@/app/lib/supabaseClient";
import RequireRole from "@/app/components/RequireRole";
import { UploadForm } from "@/app/components/dj/UploadForm";
import { TrackListItem } from "@/app/components/dj/TrackListItem";
import { AlbumListItem } from "@/app/components/dj/AlbumListItem";
import { EarningsCard } from "@/app/components/dj/EarningsCard";
import { SubscriberStats } from "@/app/components/dj/SubscriberStats";
import { PayoutPreview } from "@/app/components/dj/PayoutPreview";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorBanner } from "@/app/components/ui/ErrorBanner";
import { Upload, Music, Package, DollarSign, Users, Wallet, Loader2, Share2 } from "lucide-react";
import { DJReferralSummary } from "@/app/components/dj/DJReferralSummary";
import { motion } from "framer-motion";

type TabType = 'upload' | 'tracks' | 'albums' | 'earnings' | 'subscribers' | 'payouts' | 'referrals';

interface Track {
  id: string;
  title: string;
  price: number;
  created_at: string;
  purchase_count?: number;
}

interface Album {
  id: string;
  title: string;
  description: string | null;
  price: number;
  file_size: number;
  created_at: string;
  purchase_count?: number;
}

interface EarningsData {
  total: number;
  monthly: number;
  tracks: number;
  albums: number;
}

interface SubscriberData {
  total: number;
  basic: number;
  pro: number;
  super: number;
  active: number;
  expired: number;
}

export default function DJDashboardPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<TabType>('upload');
  const [tracks, setTracks] = useState<Track[]>([]);
  const [albums, setAlbums] = useState<Album[]>([]);
  const [earnings, setEarnings] = useState<EarningsData>({
    total: 0,
    monthly: 0,
    tracks: 0,
    albums: 0,
  });
  const [subscribers, setSubscribers] = useState<SubscriberData>({
    total: 0,
    basic: 0,
    pro: 0,
    super: 0,
    active: 0,
    expired: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [djProfileId, setDjProfileId] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    if (user) {
      loadDashboardData();
    }
  }, [user]);

  async function loadDashboardData() {
    try {
      setLoading(true);
      setError(null);

      // Get DJ profile
      const { data: djProfile, error: djError } = await supabase
        .from('dj_profiles')
        .select('id')
        .eq('user_id', user!.id)
        .single();

      if (djError) {
        // Handle case where profile might not be synced yet
        console.warn('DJ profile not found, might need sync');
        // We'll try to fetch with user ID for album packs at least
      }

      const currentDjProfileId = djProfile?.id || null;
      setDjProfileId(currentDjProfileId);

      // Fetch tracks and albums
      await loadContent(currentDjProfileId, user!.id);

      // Fetch earnings
      await loadEarnings(currentDjProfileId, user!.id);

      // Fetch subscribers
      if (currentDjProfileId) {
        await loadSubscribers(currentDjProfileId);
      }

    } catch (err: any) {
      console.error('[DJ_DASHBOARD_ERROR]', err);
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }

  async function loadContent(currentDjId: string | null, profileId: string) {
    let tracksData: any[] = [];
    if (currentDjId) {
      const { data, error } = await supabase
        .from('tracks')
        .select('id, title, price, created_at')
        .eq('dj_id', currentDjId)
        .order('created_at', { ascending: false });
      if (error) throw error;
      tracksData = data || [];
    }

    // Fetch albums
    const { data: albumsData, error: albumsError } = await supabase
      .from('album_packs')
      .select('id, title, description, price, file_size, created_at')
      .eq('dj_id', profileId)
      .order('created_at', { ascending: false });

    if (albumsError) throw albumsError;

    // Get purchase counts
    const trackIds = tracksData.map(t => t.id);
    const albumIds = (albumsData || []).map(a => a.id);

    let trackCounts: Record<string, number> = {};
    if (trackIds.length > 0) {
      const { data: trackPurchases } = await supabase
        .from('purchases')
        .select('content_id')
        .eq('content_type', 'track')
        .in('content_id', trackIds);

      trackCounts = (trackPurchases || []).reduce((acc: any, p) => {
        acc[p.content_id] = (acc[p.content_id] || 0) + 1;
        return acc;
      }, {});
    }

    let albumCounts: Record<string, number> = {};
    if (albumIds.length > 0) {
      const { data: albumPurchases } = await supabase
        .from('purchases')
        .select('content_id')
        .eq('content_type', 'zip')
        .in('content_id', albumIds);

      albumCounts = (albumPurchases || []).reduce((acc: any, p) => {
        acc[p.content_id] = (acc[p.content_id] || 0) + 1;
        return acc;
      }, {});
    }

    setTracks(tracksData.map(t => ({
      ...t,
      purchase_count: trackCounts[t.id] || 0,
    })));

    setAlbums((albumsData || []).map(a => ({
      ...a,
      purchase_count: albumCounts[a.id] || 0,
    })));
  }

  async function loadEarnings(currentDjId: string | null, profileId: string) {
    let trackIds: string[] = [];
    if (currentDjId) {
      const { data } = await supabase
        .from('tracks')
        .select('id')
        .eq('dj_id', currentDjId);
      trackIds = (data || []).map(t => t.id);
    }

    const { data: albumsData } = await supabase
      .from('album_packs')
      .select('id')
      .eq('dj_id', profileId);
    const albumIds = (albumsData || []).map(a => a.id);

    // Fetch purchases
    let trackPurchases: any[] = [];
    if (trackIds.length > 0) {
      const { data } = await supabase
        .from('purchases')
        .select('price, created_at')
        .eq('content_type', 'track')
        .in('content_id', trackIds);
      trackPurchases = data || [];
    }

    let albumPurchases: any[] = [];
    if (albumIds.length > 0) {
      const { data } = await supabase
        .from('purchases')
        .select('price, created_at')
        .eq('content_type', 'zip')
        .in('content_id', albumIds);
      albumPurchases = data || [];
    }

    // Calculate earnings
    const trackEarnings = trackPurchases.reduce((sum, p) => sum + p.price, 0);
    const albumEarnings = albumPurchases.reduce((sum, p) => sum + p.price, 0);
    const totalEarnings = trackEarnings + albumEarnings;

    // Calculate monthly earnings
    const thisMonth = new Date();
    thisMonth.setDate(1);
    thisMonth.setHours(0, 0, 0, 0);

    const allPurchases = [...trackPurchases, ...albumPurchases];
    const monthlyEarnings = allPurchases
      .filter(p => new Date(p.created_at) >= thisMonth)
      .reduce((sum, p) => sum + p.price, 0);

    setEarnings({
      total: totalEarnings,
      monthly: monthlyEarnings,
      tracks: trackEarnings,
      albums: albumEarnings,
    });
  }

  async function loadSubscribers(currentDjId: string) {
    const { data: subscriptions } = await supabase
      .from('dj_subscriptions')
      .select('plan, expires_at')
      .eq('dj_id', currentDjId);

    if (!subscriptions) {
      setSubscribers({
        total: 0,
        basic: 0,
        pro: 0,
        super: 0,
        active: 0,
        expired: 0,
      });
      return;
    }

    const now = new Date();
    const active = subscriptions.filter(s => new Date(s.expires_at) > now);
    const expired = subscriptions.filter(s => new Date(s.expires_at) <= now);

    setSubscribers({
      total: subscriptions.length,
      basic: subscriptions.filter(s => s.plan === 'basic').length,
      pro: subscriptions.filter(s => s.plan === 'pro').length,
      super: subscriptions.filter(s => s.plan === 'super').length,
      active: active.length,
      expired: expired.length,
    });
  }

  async function handleEdit(id: string, type: 'track' | 'album') {
    // In a real app, this would open a modal with a form
    const title = prompt("Enter new title:");
    if (!title) return;

    const priceStr = prompt("Enter new price (INR):");
    const price = priceStr ? Number(priceStr) : null;
    if (price === null || isNaN(price)) return;

    try {
      const endpoint = type === 'track' ? `/api/dj/tracks/${id}` : `/api/dj/albums/${id}`;
      const res = await fetch(endpoint, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, price }),
      });

      if (!res.ok) throw new Error('Update failed');

      // Reload content
      await loadContent(djProfileId, user!.id);
    } catch (err: any) {
      alert(`Failed to update ${type}: ${err.message}`);
    }
  }

  async function handleDelete(id: string, type: 'track' | 'album') {
    if (!confirm(`Are you sure you want to delete this ${type}? This action cannot be undone.`)) {
      return;
    }

    try {
      const endpoint = type === 'track' ? `/api/dj/tracks/${id}` : `/api/dj/albums/${id}`;
      const res = await fetch(endpoint, {
        method: 'DELETE',
      });

      if (!res.ok) throw new Error('Delete failed');

      // Reload content
      await loadContent(djProfileId, user!.id);
    } catch (err: any) {
      console.error(`Failed to delete ${type}:`, err);
      alert(`Failed to delete ${type}: ${err.message}`);
    }
  }

  const tabs = [
    { id: 'upload' as TabType, label: 'Upload', icon: Upload },
    { id: 'tracks' as TabType, label: 'My Tracks', icon: Music, count: tracks.length },
    { id: 'albums' as TabType, label: 'My Albums', icon: Package, count: albums.length },
    { id: 'earnings' as TabType, label: 'Earnings', icon: DollarSign },
    { id: 'subscribers' as TabType, label: 'Subscribers', icon: Users, count: subscribers.total },
    { id: 'payouts' as TabType, label: 'Payouts', icon: Wallet },
    { id: 'referrals' as TabType, label: 'Referrals', icon: Share2 },
  ];

  return (
    <RequireRole allowed={["dj", "admin"]}>
      <div className="min-h-screen pb-24">
        <div className="px-6 md:px-12">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <motion.div
              initial={mounted ? { opacity: 0, y: 20 } : false}
              animate={mounted ? { opacity: 1, y: 0 } : {}}
              className="mb-8"
            >
              <h1 className="text-4xl md:text-5xl font-bold text-white mb-3">
                DJ <span className="text-violet-400">Dashboard</span>
              </h1>
              <p className="text-zinc-500">
                Manage your content, track earnings, and grow your audience
              </p>
            </motion.div>

            {/* Error State */}
            {error && (
              <motion.div
                initial={mounted ? { opacity: 0, scale: 0.95 } : false}
                animate={mounted ? { opacity: 1, scale: 1 } : {}}
                className="mb-8"
              >
                <ErrorBanner
                  title="Failed to load dashboard"
                  message={error}
                  action={{
                    label: "Try Again",
                    onClick: loadDashboardData
                  }}
                  variant="error"
                />
              </motion.div>
            )}

            {/* Loading State */}
            {loading && (
              <div className="flex items-center justify-center py-32">
                <Loader2 className="animate-spin text-violet-400" size={48} />
              </div>
            )}

            {/* Dashboard Content */}
            {!loading && !error && (
              <>
                {/* Quick Stats */}
                <motion.div
                  initial={mounted ? { opacity: 0, y: 20 } : false}
                  animate={mounted ? { opacity: 1, y: 0 } : {}}
                  transition={{ delay: 0.1 }}
                  className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
                >
                  <div className="p-6 rounded-2xl bg-emerald-600/10 border border-emerald-500/30">
                    <p className="text-sm text-zinc-500 font-semibold mb-1">Total Earnings</p>
                    <p className="text-3xl font-extrabold text-emerald-400">
                      ₹{earnings.total.toLocaleString('en-IN')}
                    </p>
                  </div>
                  <div className="p-6 rounded-2xl bg-violet-600/10 border border-violet-500/30">
                    <p className="text-sm text-zinc-500 font-semibold mb-1">Subscribers</p>
                    <p className="text-3xl font-extrabold text-violet-400">{subscribers.active}</p>
                  </div>
                  <div className="p-6 rounded-2xl bg-violet-600/10 border border-violet-500/30">
                    <p className="text-sm text-zinc-500 font-semibold mb-1">Tracks</p>
                    <p className="text-3xl font-extrabold text-violet-400">{tracks.length}</p>
                  </div>
                  <div className="p-6 rounded-2xl bg-amber-600/10 border border-amber-500/30">
                    <p className="text-sm text-zinc-500 font-semibold mb-1">Albums</p>
                    <p className="text-3xl font-extrabold text-amber-400">{albums.length}</p>
                  </div>
                </motion.div>

                {/* Tabs */}
                <motion.div
                  initial={mounted ? { opacity: 0, y: 20 } : false}
                  animate={mounted ? { opacity: 1, y: 0 } : {}}
                  transition={{ delay: 0.2 }}
                  className="mb-8"
                >
                  <div className="flex flex-wrap gap-2 border-b border-zinc-800/60 pb-4">
                    {tabs.map((tab) => {
                      const Icon = tab.icon;
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm transition-all duration-300 ${activeTab === tab.id
                            ? 'bg-violet-600 text-white shadow-lg shadow-violet-500/30'
                            : 'bg-zinc-900/60 text-zinc-400 hover:text-white hover:bg-zinc-800/60'
                            }`}
                        >
                          <Icon size={18} />
                          {tab.label}
                          {tab.count !== undefined && (
                            <span className={`px-2 py-0.5 rounded-lg text-xs font-bold ${activeTab === tab.id
                              ? 'bg-white/20 text-white'
                              : 'bg-zinc-800/60 text-zinc-500'
                              }`}>
                              {tab.count}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </motion.div>

                {/* Tab Content */}
                <motion.div
                  key={activeTab}
                  initial={mounted ? { opacity: 0, y: 20 } : false}
                  animate={mounted ? { opacity: 1, y: 0 } : {}}
                  transition={{ delay: 0.1 }}
                >
                  {/* Upload Tab */}
                  {activeTab === 'upload' && (
                    <div className="space-y-8">
                      <UploadForm type="track" onSuccess={loadDashboardData} />
                      <UploadForm type="album" onSuccess={loadDashboardData} />
                    </div>
                  )}

                  {/* Tracks Tab */}
                  {activeTab === 'tracks' && (
                    <>
                      {tracks.length === 0 ? (
                        <EmptyState
                          icon={<Music size={40} />}
                          title="No Tracks Uploaded"
                          description="Upload your first track to start selling your music!"
                          action={{
                            label: "Upload Track",
                            onClick: () => setActiveTab('upload')
                          }}
                        />
                      ) : (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          {tracks.map((track) => (
                            <TrackListItem
                              key={track.id}
                              id={track.id}
                              title={track.title}
                              price={track.price}
                              createdAt={track.created_at}
                              purchaseCount={track.purchase_count}
                              onEdit={(id) => handleEdit(id, 'track')}
                              onDelete={(id) => handleDelete(id, 'track')}
                            />
                          ))}
                        </div>
                      )}
                    </>
                  )}

                  {/* Albums Tab */}
                  {activeTab === 'albums' && (
                    <>
                      {albums.length === 0 ? (
                        <EmptyState
                          icon={<Package size={40} />}
                          title="No Albums Uploaded"
                          description="Upload an album pack to offer bundled content to your fans!"
                          action={{
                            label: "Upload Album",
                            onClick: () => setActiveTab('upload')
                          }}
                        />
                      ) : (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          {albums.map((album) => (
                            <AlbumListItem
                              key={album.id}
                              id={album.id}
                              title={album.title}
                              description={album.description}
                              price={album.price}
                              fileSize={album.file_size}
                              createdAt={album.created_at}
                              purchaseCount={album.purchase_count}
                              onEdit={(id) => handleEdit(id, 'album')}
                              onDelete={(id) => handleDelete(id, 'album')}
                            />
                          ))}
                        </div>
                      )}
                    </>
                  )}

                  {/* Earnings Tab */}
                  {activeTab === 'earnings' && (
                    <EarningsCard
                      totalEarnings={earnings.total}
                      monthlyEarnings={earnings.monthly}
                      trackEarnings={earnings.tracks}
                      albumEarnings={earnings.albums}
                    />
                  )}

                  {/* Subscribers Tab */}
                  {activeTab === 'subscribers' && (
                    <SubscriberStats
                      totalSubscribers={subscribers.total}
                      basicCount={subscribers.basic}
                      proCount={subscribers.pro}
                      superCount={subscribers.super}
                      activeCount={subscribers.active}
                      expiredCount={subscribers.expired}
                    />
                  )}

                  {/* Payouts Tab */}
                  {activeTab === 'payouts' && (
                    <PayoutPreview
                      availableBalance={earnings.total}
                      pendingBalance={0}
                    />
                  )}

                  {/* Referrals Tab */}
                  {activeTab === 'referrals' && (
                    <DJReferralSummary />
                  )}
                </motion.div>
              </>
            )}
          </div>
        </div>
      </div>
    </RequireRole>
  );
}
