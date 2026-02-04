"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/app/lib/AuthContext";
import { supabase } from "@/app/lib/supabaseClient";
import RequireRole from "@/app/components/RequireRole";
import { QuickStats } from "@/app/components/dashboard/QuickStats";
import { PurchaseCard } from "@/app/components/dashboard/PurchaseCard";
import { SubscriptionCard } from "@/app/components/dashboard/SubscriptionCard";
import { DownloadCard } from "@/app/components/dashboard/DownloadCard";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorBanner } from "@/app/components/ui/ErrorBanner";
import { ShoppingBag, Users, Download, Loader2, Gift } from "lucide-react";
import { RewardsDashboard } from "@/app/components/rewards/RewardsDashboard";
import { motion } from "framer-motion";

type TabType = 'purchases' | 'subscriptions' | 'downloads' | 'rewards';

interface Purchase {
  id: string;
  content_type: 'track' | 'zip';
  content_id: string;
  created_at: string;
  title?: string;
  dj_name?: string;
  dj_slug?: string;
}

interface Subscription {
  id: string;
  dj_id: string;
  plan: 'basic' | 'pro' | 'super';
  track_quota: number;
  zip_quota: number;
  fan_upload_quota: number;
  expires_at: string;
  created_at: string;
  dj_name?: string;
  dj_slug?: string;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<TabType>('purchases');
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

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

      // Fetch purchases
      const { data: purchasesData, error: purchasesError } = await supabase
        .from('purchases')
        .select('*')
        .eq('user_id', user!.id)
        .order('created_at', { ascending: false });

      if (purchasesError) throw purchasesError;

      // Enrich purchases with content details
      const enrichedPurchases = await Promise.all(
        (purchasesData || []).map(async (purchase) => {
          const table = purchase.content_type === 'track' ? 'tracks' : 'album_packs';
          const { data: content } = await supabase
            .from(table)
            .select(`
              title,
              dj_profiles:${purchase.content_type === 'track' ? 'dj_id' : 'dj_profile_id'} (
                dj_name,
                slug
              )
            `)
            .eq('id', purchase.content_id)
            .single();

          return {
            ...purchase,
            title: content?.title || 'Unknown',
            dj_name: content?.dj_profiles?.dj_name || 'Unknown DJ',
            dj_slug: content?.dj_profiles?.slug || '',
          };
        })
      );

      setPurchases(enrichedPurchases);

      // Fetch subscriptions
      const { data: subscriptionsData, error: subscriptionsError } = await supabase
        .from('dj_subscriptions')
        .select(`
          *,
          dj_profiles:dj_id (
            dj_name,
            slug
          )
        `)
        .eq('user_id', user!.id)
        .order('created_at', { ascending: false });

      if (subscriptionsError) throw subscriptionsError;

      const enrichedSubscriptions = (subscriptionsData || []).map((sub: any) => ({
        ...sub,
        dj_name: sub.dj_profiles?.dj_name || 'Unknown DJ',
        dj_slug: sub.dj_profiles?.slug || '',
      }));

      setSubscriptions(enrichedSubscriptions);

    } catch (err: any) {
      console.error('[DASHBOARD_ERROR]', err);
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }

  async function handleDownload(contentId: string, contentType: string) {
    try {
      setDownloadingId(contentId);

      const res = await fetch('/api/download-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content_id: contentId,
          content_type: contentType
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to generate download token');
      }

      const { token } = await res.json();
      window.location.href = `/api/download?token=${token}`;

    } catch (err: any) {
      console.error('[DOWNLOAD_ERROR]', err);
      alert('Failed to download. Please try again.');
    } finally {
      setDownloadingId(null);
    }
  }

  // Calculate stats
  const activeSubscriptions = subscriptions.filter(
    sub => new Date(sub.expires_at) > new Date()
  );
  const totalDownloads = purchases.length + activeSubscriptions.length;

  // Get downloads list (purchases + subscription content)
  const downloadsList = purchases.map(p => ({
    ...p,
    accessType: 'purchased' as const,
  }));

  const tabs = [
    { id: 'purchases' as TabType, label: 'Purchases', icon: ShoppingBag, count: purchases.length },
    { id: 'subscriptions' as TabType, label: 'Subscriptions', icon: Users, count: subscriptions.length },
    { id: 'downloads' as TabType, label: 'Downloads', icon: Download, count: downloadsList.length },
    { id: 'rewards' as TabType, label: 'Rewards', icon: Gift },
  ];

  return (
    <RequireRole allowed={["user", "dj", "admin"]}>
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
                My <span className="text-violet-400">Dashboard</span>
              </h1>
              <p className="text-zinc-500">
                Manage your purchases, subscriptions, and downloads
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
                >
                  <QuickStats
                    totalPurchases={purchases.length}
                    activeSubscriptions={activeSubscriptions.length}
                    totalDownloads={totalDownloads}
                  />
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
                          <span className={`px-2 py-0.5 rounded-lg text-xs font-bold ${activeTab === tab.id
                            ? 'bg-white/20 text-white'
                            : 'bg-zinc-800/60 text-zinc-500'
                            }`}>
                            {tab.count}
                          </span>
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
                  {/* Purchases Tab */}
                  {activeTab === 'purchases' && (
                    <>
                      {purchases.length === 0 ? (
                        <EmptyState
                          icon={<ShoppingBag size={40} />}
                          title="No Purchases Yet"
                          description="You haven't purchased any tracks or albums yet. Explore our collection to find your favorite music!"
                          action={{
                            label: "Explore Tracks",
                            href: "/tracks"
                          }}
                        />
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                          {purchases.map((purchase) => (
                            <PurchaseCard
                              key={purchase.id}
                              id={purchase.content_id}
                              title={purchase.title!}
                              djName={purchase.dj_name!}
                              djSlug={purchase.dj_slug!}
                              type={purchase.content_type}
                              purchaseDate={purchase.created_at}
                              onDownload={handleDownload}
                              downloading={downloadingId === purchase.content_id}
                            />
                          ))}
                        </div>
                      )}
                    </>
                  )}

                  {/* Subscriptions Tab */}
                  {activeTab === 'subscriptions' && (
                    <>
                      {subscriptions.length === 0 ? (
                        <EmptyState
                          icon={<Users size={40} />}
                          title="No Active Subscriptions"
                          description="Subscribe to your favorite DJs to get unlimited access to their content!"
                          action={{
                            label: "Explore DJs",
                            href: "/explore"
                          }}
                        />
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                          {subscriptions.map((subscription) => (
                            <SubscriptionCard
                              key={subscription.id}
                              id={subscription.id}
                              djName={subscription.dj_name!}
                              djSlug={subscription.dj_slug!}
                              plan={subscription.plan}
                              expiresAt={subscription.expires_at}
                              isActive={new Date(subscription.expires_at) > new Date()}
                              trackQuota={subscription.track_quota}
                              zipQuota={subscription.zip_quota}
                              fanUploadQuota={subscription.fan_upload_quota}
                            />
                          ))}
                        </div>
                      )}
                    </>
                  )}

                  {/* Downloads Tab */}
                  {activeTab === 'downloads' && (
                    <>
                      {downloadsList.length === 0 ? (
                        <EmptyState
                          icon={<Download size={40} />}
                          title="No Downloads Available"
                          description="Purchase tracks or subscribe to DJs to access downloadable content."
                          action={{
                            label: "Browse Music",
                            href: "/tracks"
                          }}
                        />
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                          {downloadsList.map((item) => (
                            <DownloadCard
                              key={item.id}
                              id={item.content_id}
                              title={item.title!}
                              djName={item.dj_name!}
                              djSlug={item.dj_slug!}
                              type={item.content_type}
                              accessType={item.accessType}
                              onDownload={handleDownload}
                              downloading={downloadingId === item.content_id}
                            />
                          ))}
                        </div>
                      )}
                    </>
                  )}

                  {/* Rewards Tab */}
                  {activeTab === 'rewards' && (
                    <RewardsDashboard />
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