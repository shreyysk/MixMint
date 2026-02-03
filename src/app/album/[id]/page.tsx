"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/app/lib/supabaseClient";
import { useAuth } from "@/app/lib/AuthContext";
import { Button } from "@/app/components/ui/Button";
import { Loader2, Package, Download, FileArchive, ArrowLeft } from "lucide-react";
import { motion } from "framer-motion";
import Link from "next/link";
import { purchaseContent } from "@/app/lib/razorpayCheckout";

interface Album {
  id: string;
  title: string;
  description: string | null;
  price: number;
  file_size: number;
  dj_id: string;
  dj_profile_id: string;
  dj_profile?: {
    dj_name: string;
    slug: string;
  };
}

export default function AlbumDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const albumId = params?.id as string;

  const [album, setAlbum] = useState<Album | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [purchasing, setPurchasing] = useState(false);

  useEffect(() => {
    if (albumId) {
      loadAlbum();
    }
  }, [albumId]);

  async function loadAlbum() {
    try {
      setLoading(true);
      setError(null);

      const { data, error: fetchError } = await supabase
        .from("album_packs")
        .select(`
          id,
          title,
          description,
          price,
          file_size,
          dj_id,
          dj_profile_id,
          dj_profiles:dj_profile_id (
            dj_name,
            slug
          )
        `)
        .eq("id", albumId)
        .single();

      if (fetchError) throw fetchError;
      if (!data) throw new Error("Album not found");

      const transformedData = {
        ...data,
        dj_profile: Array.isArray(data.dj_profiles) 
          ? data.dj_profiles[0] 
          : data.dj_profiles
      };

      setAlbum(transformedData);
    } catch (err: any) {
      console.error("[ALBUM_LOAD_ERROR]", err);
      setError(err.message || "Failed to load album");
    } finally {
      setLoading(false);
    }
  }

  function formatFileSize(bytes: number): string {
    const mb = bytes / (1024 * 1024);
    return mb.toFixed(2) + " MB";
  }

  async function handlePurchase() {
    if (!user) {
      alert("Please log in to purchase");
      router.push("/auth/login");
      return;
    }

    if (!album) return;

    setPurchasing(true);

    try {
      await purchaseContent({
        contentId: album.id,
        contentType: "zip",
        userEmail: user.email || undefined,
        userName: user.user_metadata?.full_name || undefined,
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

      const res = await fetch("/api/download-token", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}` 
        },
        body: JSON.stringify({ 
          content_id: albumId, 
          content_type: "zip" 
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.error || "Download failed");
        return;
      }

      window.location.href = `/api/download?token=${data.token}`;
    } catch (err: any) {
      console.error("[FREE_DOWNLOAD_ERROR]", err);
      alert("Download failed: " + err.message);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="loading-state">
        <Loader2 className="animate-spin text-amber-500" size={48} />
      </div>
    );
  }

  if (error || !album) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6" data-testid="error-state">
        <div className="text-center max-w-md">
          <Package className="text-red-500 mx-auto mb-4" size={64} />
          <h1 className="text-3xl font-black text-white uppercase mb-2">Album Not Found</h1>
          <p className="text-zinc-500 font-bold mb-6">{error || "This album doesn't exist."}</p>
          <Link href="/albums">
            <Button>Browse All Albums</Button>
          </Link>
        </div>
      </div>
    );
  }

  const isFree = album.price === 0;

  return (
    <div className="min-h-screen pb-24" data-testid="album-detail-page">
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
            
            {/* Left: Album Artwork */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="aspect-square rounded-3xl bg-gradient-to-br from-amber-600/20 to-orange-600/20 border border-amber-500/30 flex items-center justify-center overflow-hidden">
                <FileArchive className="text-amber-500/50" size={120} />
              </div>

              {/* File Info */}
              <div className="mt-6 p-6 rounded-2xl bg-zinc-900/40 border border-zinc-800">
                <div className="flex items-center gap-3 mb-3">
                  <Package className="text-amber-500" size={20} />
                  <span className="font-black text-white uppercase text-sm">Package Details</span>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-zinc-500 font-bold">Format:</span>
                    <span className="text-white font-bold">ZIP Archive</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500 font-bold">Size:</span>
                    <span className="text-white font-bold">{formatFileSize(album.file_size)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500 font-bold">Contents:</span>
                    <span className="text-white font-bold">Multiple Tracks</span>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Right: Album Details & Purchase */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              
              {/* Album Title */}
              <h1 className="text-5xl font-black text-white uppercase italic tracking-tighter mb-4">
                {album.title}
              </h1>

              {/* DJ Info */}
              {album.dj_profile && (
                <Link 
                  href={`/dj/${album.dj_profile.slug}`}
                  className="inline-block mb-6"
                >
                  <div className="text-zinc-500 hover:text-amber-400 transition-colors font-bold">
                    by <span className="text-white">{album.dj_profile.dj_name}</span>
                  </div>
                </Link>
              )}

              {/* Description */}
              {album.description && (
                <p className="text-zinc-400 leading-relaxed mb-8">
                  {album.description}
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
                      This album pack is available for free!
                    </p>
                    <Button
                      onClick={handleFreeDownload}
                      size="lg"
                      className="w-full bg-green-600 hover:bg-green-700"
                      data-testid="free-download-btn"
                    >
                      <Download size={20} />
                      Free Download ZIP
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
                          ₹{album.price}
                        </div>
                      </div>
                      <FileArchive className="text-amber-500/30" size={48} />
                    </div>
                    
                    <Button
                      onClick={handlePurchase}
                      disabled={purchasing}
                      size="lg"
                      className="w-full bg-amber-600 hover:bg-amber-700"
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
                          Buy Pack - ₹{album.price}
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
              <div className="p-6 rounded-xl bg-amber-600/10 border border-amber-500/30">
                <p className="text-amber-400 text-sm font-bold">
                  ✓ Complete album collection<br/>
                  ✓ High-quality audio files<br/>
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
