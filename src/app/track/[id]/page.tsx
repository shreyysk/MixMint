
"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/app/lib/supabaseClient";
import { useAuth } from "@/app/lib/AuthContext";
import { Button } from "@/app/components/ui/Button";
import { Loader2, Music, Download, Play, ArrowLeft, ExternalLink, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import Link from "next/link";
import { purchaseContent } from "@/app/lib/razorpayCheckout";

interface Track {
  id: string;
  title: string;
  description: string | null;
  price: number;
  youtube_url: string | null;
  dj_id: string;
  dj_profile?: {
    dj_name: string;
    slug: string;
  };
}

export default function TrackDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const trackId = params?.id as string;

  const [track, setTrack] = useState<Track | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [purchasing, setPurchasing] = useState(false);
  const [userPoints, setUserPoints] = useState(0);
  const [redeemPoints, setRedeemPoints] = useState(false);
  const [pointsToRedeem, setPointsToRedeem] = useState(0);

  useEffect(() => {
    if (trackId) {
      loadTrack();
    }
    if (user) {
      loadUserPoints();
    }
  }, [trackId, user]);

  async function loadTrack() {
    try {
      setLoading(true);
      setError(null);

      const { data, error: fetchError } = await supabase
        .from("tracks")
        .select(`
          id,
          title,
          description,
          price,
          youtube_url,
          dj_id,
          dj_profiles:dj_id (
            dj_name,
            slug
          )
        `)
        .eq("id", trackId)
        .eq("status", "active")
        .single();

      if (fetchError) throw fetchError;
      if (!data) throw new Error("Track not found");

      // Transform nested data
      const transformedData = {
        ...data,
        dj_profile: Array.isArray(data.dj_profiles) 
          ? data.dj_profiles[0] 
          : data.dj_profiles
      };

      setTrack(transformedData);
    } catch (err: any) {
      console.error("[TRACK_LOAD_ERROR]", err);
      setError(err.message || "Failed to load track");
    } finally {
      setLoading(false);
    }
  }

  async function loadUserPoints() {
    const { data, error } = await supabase
      .from('points')
      .select('balance')
      .eq('user_id', user!.id)
      .single();

    if (data) {
      setUserPoints(data.balance);
    }
  }

  async function handlePurchase() {
    if (!user) {
      alert("Please log in to purchase");
      router.push("/auth/login");
      return;
    }

    if (!track) return;

    setPurchasing(true);

    try {
      await purchaseContent({
        contentId: track.id,
        contentType: "track",
        userEmail: user.email || undefined,
        userName: user.user_metadata?.full_name || undefined,
        pointsToRedeem: redeemPoints ? pointsToRedeem : 0,
        onSuccess: () => {
          console.log("Purchase successful");
        },
        onFailure: (error) => {
          console.error("Purchase failed:", error);
          alert(`Purchase failed: ${error}`);
        }
      });
    } catch (err: any) {
      console.error("[PURCHASE_ERROR]", err);
      alert(`Purchase failed: ${err.message}`);
    } finally {
      setPurchasing(false);
    }
  }

  async function handleFreeDownload() {
    if (!user) {
      alert("Please log in to download");
      router.push("/auth/login");
      return;
    }

    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        alert("Please log in");
        return;
      }

      // Request download token for free track
      const res = await fetch("/api/download-token", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}` 
        },
        body: JSON.stringify({ 
          content_id: trackId, 
          content_type: "track" 
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.error || "Download failed");
        return;
      }

      // Redirect to download
      window.location.href = `/api/download?token=${data.token}`;
    } catch (err: any) {
      console.error("[FREE_DOWNLOAD_ERROR]", err);
      alert("Download failed: " + err.message);
    }
  }

  // Loading State
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="loading-state">
        <Loader2 className="animate-spin text-violet-500" size={48} />
      </div>
    );
  }

  // Error State
  if (error || !track) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6" data-testid="error-state">
        <div className="text-center max-w-md">
          <Music className="text-red-500 mx-auto mb-4" size={64} />
          <h1 className="text-3xl font-black text-white uppercase mb-2">Track Not Found</h1>
          <p className="text-zinc-500 font-bold mb-6">{error || "This track doesn't exist."}</p>
          <Link href="/tracks">
            <Button>Browse All Tracks</Button>
          </Link>
        </div>
      </div>
    );
  }

  const isFree = track.price === 0;
  const finalPrice = track.price - (redeemPoints ? Math.min(pointsToRedeem, track.price, Math.floor(track.price * 0.2)) : 0);

  return (
    <div className="min-h-screen pb-24" data-testid="track-detail-page">
      <div className="px-6 md:px-12">
        <div className="max-w-5xl mx-auto pt-8">
          
          {/* Back Button */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="mb-8"
          >
            <button
              onClick={() => router.back()}
              className="flex items-center gap-2 text-zinc-500 hover:text-white transition-colors"
            >
              <ArrowLeft size={20} />
              <span className="font-bold">Back</span>
            </button>
          </motion.div>

          {/* Main Content */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            
            {/* Left: Track Artwork & Preview */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {/* Artwork Placeholder */}
              <div className="aspect-square rounded-3xl bg-gradient-to-br from-violet-600/20 to-indigo-600/20 border border-violet-500/30 flex items-center justify-center mb-6 overflow-hidden">
                <Music className="text-violet-500/50" size={120} />
              </div>

              {/* YouTube Preview */}
              {track.youtube_url && (
                <div className="p-6 rounded-2xl bg-zinc-900/40 border border-zinc-800">
                  <div className="flex items-center gap-2 mb-4">
                    <Play className="text-red-500" size={20} />
                    <span className="font-black text-white uppercase text-sm">Preview</span>
                  </div>
                  <a
                    href={track.youtube_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-zinc-400 hover:text-violet-400 transition-colors"
                  >
                    <span className="text-sm font-bold">Watch on YouTube</span>
                    <ExternalLink size={16} />
                  </a>
                </div>
              )}
            </motion.div>

            {/* Right: Track Details & Purchase */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              
              {/* Track Title */}
              <h1 className="text-5xl font-black text-white uppercase italic tracking-tighter mb-4">
                {track.title}
              </h1>

              {/* DJ Info */}
              {track.dj_profile && (
                <Link 
                  href={`/dj/${track.dj_profile.slug}`}
                  className="inline-block mb-6"
                >
                  <div className="text-zinc-500 hover:text-violet-400 transition-colors font-bold">
                    by <span className="text-white">{track.dj_profile.dj_name}</span>
                  </div>
                </Link>
              )}

              {/* Description */}
              {track.description && (
                <p className="text-zinc-400 leading-relaxed mb-8">
                  {track.description}
                </p>
              )}

              {/* Price & Purchase Section */}
              <div className="p-8 rounded-2xl bg-zinc-900/40 border border-zinc-800 mb-6">
                {isFree ? (
                  <>
                    <div className="flex items-center gap-3 mb-4">
                      <Download className="text-green-500" size={24} />
                      <span className="text-2xl font-black text-white uppercase italic">
                        Free Download
                      </span>
                    </div>
                    <p className="text-zinc-500 text-sm font-bold mb-6">
                      This track is available for free. Download and enjoy!
                    </p>
                    <Button
                      onClick={handleFreeDownload}
                      size="lg"
                      className="w-full bg-green-600 hover:bg-green-700"
                      data-testid="free-download-btn"
                    >
                      <Download size={20} />
                      Free Download
                    </Button>
                  </>
                ) : (
                  <>
                    <div className="flex items-center justify-between mb-6">
                      <div>
                        <div className="text-zinc-500 text-sm font-bold uppercase tracking-wider mb-1">
                          Price
                        </div>
                        <div className="text-4xl font-black text-white italic">
                          ₹{track.price}
                        </div>
                      </div>
                      <Music className="text-violet-500/30" size={48} />
                    </div>

                    {userPoints > 0 && (
                      <div className="mb-4 p-4 rounded-lg bg-yellow-400/10 border border-yellow-400/30">
                          <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                  <Sparkles size={16} className="text-yellow-400" />
                                  <span className="text-yellow-400 font-bold">You have {userPoints} points</span>
                              </div>
                              <input type="checkbox" checked={redeemPoints} onChange={() => setRedeemPoints(!redeemPoints)} />
                          </div>
                          {redeemPoints && (
                              <div className="mt-2">
                                  <input 
                                      type="number" 
                                      className="w-full bg-transparent text-white border-b border-yellow-400/50 focus:outline-none focus:border-yellow-400"
                                      value={pointsToRedeem}
                                      onChange={(e) => setPointsToRedeem(Number(e.target.value))}
                                      max={Math.min(userPoints, Math.floor(track.price * 0.2))}
                                  />
                                  <p className="text-xs text-yellow-400/70 mt-1">Max redeemable: {Math.min(userPoints, Math.floor(track.price * 0.2))} points (20% cap)</p>
                              </div>
                          )}
                      </div>
                    )}
                    
                    <Button
                      onClick={handlePurchase}
                      disabled={purchasing}
                      size="lg"
                      className="w-full"
                      data-testid="purchase-btn"
                    >
                      {purchasing ? (
                        <>
                          <Loader2 className="animate-spin" size={20} />
                          Processing...
                        </>
                      ) : (
                        <>
                          <Download size={20} />
                          Buy Track - ₹{finalPrice}
                        </>
                      )}
                    </Button>

                    <p className="text-zinc-600 text-xs text-center mt-4">
                      Secure payment via Razorpay
                    </p>
                  </>
                )}
              </div>

              {/* Info Box */}
              <div className="p-6 rounded-xl bg-violet-600/10 border border-violet-500/30">
                <p className="text-violet-400 text-sm font-bold">
                  ✓ High-quality audio file<br/>
                  ✓ Permanent ownership<br/>
                  ✓ Download anytime from your library
                </p>
              </div>

            </motion.div>
          </div>

        </div>
      </div>
    </div>
  );
}
