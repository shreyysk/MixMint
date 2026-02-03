"use client";

import React, { useEffect, useState } from "react";
import { supabase } from "@/app/lib/supabaseClient";
import { useAuth } from "@/app/lib/AuthContext";
import RequireRole from "@/app/components/RequireRole";
import { Button } from "@/app/components/ui/Button";
import { Settings, CreditCard, DollarSign, Flag, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

interface SystemSettings {
  payment_gateway: {
    provider: "razorpay" | "phonepe";
    mode: "test" | "production";
  };
  minimum_pricing: {
    track: number;
    album: number;
    subscription_basic: number;
    subscription_pro: number;
    subscription_super: number;
  };
  feature_flags: {
    fan_uploads_enabled: boolean;
    referrals_enabled: boolean;
    custom_domains_enabled: boolean;
  };
}

export default function AdminSettingsPage() {
  const { user } = useAuth();
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [paymentProvider, setPaymentProvider] = useState<"razorpay" | "phonepe">("razorpay");
  const [paymentMode, setPaymentMode] = useState<"test" | "production">("test");
  
  const [minPrices, setMinPrices] = useState({
    track: 29,
    album: 79,
    subscription_basic: 49,
    subscription_pro: 99,
    subscription_super: 199,
  });

  const [featureFlags, setFeatureFlags] = useState({
    fan_uploads_enabled: true,
    referrals_enabled: false,
    custom_domains_enabled: false,
  });

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    try {
      setLoading(true);
      
      const { data, error } = await supabase
        .from("system_settings")
        .select("key, value");

      if (error) throw error;

      const settingsMap: any = {};
      data?.forEach((setting) => {
        settingsMap[setting.key] = setting.value;
      });

      if (settingsMap.payment_gateway) {
        setPaymentProvider(settingsMap.payment_gateway.provider);
        setPaymentMode(settingsMap.payment_gateway.mode);
      }

      if (settingsMap.minimum_pricing) {
        setMinPrices(settingsMap.minimum_pricing);
      }

      if (settingsMap.feature_flags) {
        setFeatureFlags(settingsMap.feature_flags);
      }

      setSettings(settingsMap as SystemSettings);
    } catch (err: any) {
      console.error("[SETTINGS_LOAD_ERROR]", err);
      setMessage({ type: "error", text: "Failed to load settings" });
    } finally {
      setLoading(false);
    }
  }

  async function savePaymentGateway() {
    if (!user) return;
    
    try {
      setSaving(true);
      setMessage(null);

      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        setMessage({ type: "error", text: "Not authenticated" });
        return;
      }

      const { error } = await supabase
        .from("system_settings")
        .update({
          value: { provider: paymentProvider, mode: paymentMode },
          updated_at: new Date().toISOString(),
          updated_by: user.id,
        })
        .eq("key", "payment_gateway");

      if (error) throw error;

      setMessage({ type: "success", text: "Payment gateway updated successfully" });
      
      // Reload settings
      await loadSettings();
    } catch (err: any) {
      console.error("[SAVE_GATEWAY_ERROR]", err);
      setMessage({ type: "error", text: err.message || "Failed to save settings" });
    } finally {
      setSaving(false);
    }
  }

  async function savePricing() {
    if (!user) return;
    
    try {
      setSaving(true);
      setMessage(null);

      const { error } = await supabase
        .from("system_settings")
        .update({
          value: minPrices,
          updated_at: new Date().toISOString(),
          updated_by: user.id,
        })
        .eq("key", "minimum_pricing");

      if (error) throw error;

      setMessage({ type: "success", text: "Pricing updated successfully" });
      await loadSettings();
    } catch (err: any) {
      console.error("[SAVE_PRICING_ERROR]", err);
      setMessage({ type: "error", text: err.message || "Failed to save pricing" });
    } finally {
      setSaving(false);
    }
  }

  async function saveFeatureFlags() {
    if (!user) return;
    
    try {
      setSaving(true);
      setMessage(null);

      const { error } = await supabase
        .from("system_settings")
        .update({
          value: featureFlags,
          updated_at: new Date().toISOString(),
          updated_by: user.id,
        })
        .eq("key", "feature_flags");

      if (error) throw error;

      setMessage({ type: "success", text: "Feature flags updated successfully" });
      await loadSettings();
    } catch (err: any) {
      console.error("[SAVE_FLAGS_ERROR]", err);
      setMessage({ type: "error", text: err.message || "Failed to save feature flags" });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <RequireRole allowed={["admin"]}>
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="animate-spin text-violet-500" size={48} />
        </div>
      </RequireRole>
    );
  }

  return (
    <RequireRole allowed={["admin"]}>
      <div className="pb-24" data-testid="admin-settings-page">
        <div className="px-6 md:px-12">
          <div className="max-w-5xl mx-auto">
            {/* Header */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-12"
            >
              <div className="flex items-center gap-3 mb-4">
                <Settings className="text-violet-500" size={32} />
                <h1 className="text-5xl font-black text-white uppercase italic tracking-tight">
                  System Settings
                </h1>
              </div>
              <p className="text-zinc-500 font-bold">
                Configure payment gateways, pricing, and platform features.
              </p>
            </motion.div>

            {/* Message Banner */}
            {message && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-4 rounded-xl mb-8 flex items-center gap-3 ${
                  message.type === "success"
                    ? "bg-green-900/20 border border-green-800/50"
                    : "bg-red-900/20 border border-red-800/50"
                }`}
              >
                {message.type === "success" ? (
                  <CheckCircle className="text-green-500" size={20} />
                ) : (
                  <AlertCircle className="text-red-500" size={20} />
                )}
                <span className={message.type === "success" ? "text-green-400" : "text-red-400"}>
                  {message.text}
                </span>
              </motion.div>
            )}

            {/* Payment Gateway Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="p-8 rounded-2xl bg-zinc-900/40 border border-zinc-800 mb-8"
            >
              <div className="flex items-center gap-3 mb-6">
                <CreditCard className="text-violet-500" size={24} />
                <h2 className="text-2xl font-black text-white uppercase italic tracking-tight">
                  Payment Gateway
                </h2>
              </div>

              <div className="space-y-6">
                {/* Provider Selection */}
                <div>
                  <label className="block text-sm font-bold text-zinc-400 mb-3">
                    Active Provider
                  </label>
                  <div className="flex gap-4">
                    <button
                      onClick={() => setPaymentProvider("razorpay")}
                      className={`flex-1 p-4 rounded-xl border-2 transition-all ${
                        paymentProvider === "razorpay"
                          ? "border-violet-500 bg-violet-500/10"
                          : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700"
                      }`}
                      data-testid="razorpay-option"
                    >
                      <div className="font-black text-white uppercase">Razorpay</div>
                      <div className="text-xs text-zinc-500 mt-1">Active & Configured</div>
                    </button>
                    <button
                      onClick={() => setPaymentProvider("phonepe")}
                      className={`flex-1 p-4 rounded-xl border-2 transition-all ${
                        paymentProvider === "phonepe"
                          ? "border-violet-500 bg-violet-500/10"
                          : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700"
                      }`}
                      data-testid="phonepe-option"
                    >
                      <div className="font-black text-white uppercase">PhonePe</div>
                      <div className="text-xs text-red-500 mt-1">Not Configured</div>
                    </button>
                  </div>
                </div>

                {/* Mode Selection */}
                <div>
                  <label className="block text-sm font-bold text-zinc-400 mb-3">
                    Environment Mode
                  </label>
                  <div className="flex gap-4">
                    <button
                      onClick={() => setPaymentMode("test")}
                      className={`flex-1 p-4 rounded-xl border-2 transition-all ${
                        paymentMode === "test"
                          ? "border-amber-500 bg-amber-500/10"
                          : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700"
                      }`}
                    >
                      <div className="font-black text-white uppercase">Test Mode</div>
                      <div className="text-xs text-zinc-500 mt-1">Development</div>
                    </button>
                    <button
                      onClick={() => setPaymentMode("production")}
                      className={`flex-1 p-4 rounded-xl border-2 transition-all ${
                        paymentMode === "production"
                          ? "border-green-500 bg-green-500/10"
                          : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700"
                      }`}
                    >
                      <div className="font-black text-white uppercase">Production</div>
                      <div className="text-xs text-zinc-500 mt-1">Live Payments</div>
                    </button>
                  </div>
                </div>

                <Button
                  onClick={savePaymentGateway}
                  disabled={saving}
                  className="w-full"
                  data-testid="save-payment-gateway"
                >
                  {saving ? "Saving..." : "Save Payment Gateway"}
                </Button>
              </div>
            </motion.div>

            {/* Minimum Pricing Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="p-8 rounded-2xl bg-zinc-900/40 border border-zinc-800 mb-8"
            >
              <div className="flex items-center gap-3 mb-6">
                <DollarSign className="text-green-500" size={24} />
                <h2 className="text-2xl font-black text-white uppercase italic tracking-tight">
                  Minimum Pricing (INR)
                </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-bold text-zinc-400 mb-2">Track</label>
                  <input
                    type="number"
                    value={minPrices.track}
                    onChange={(e) => setMinPrices({ ...minPrices, track: Number(e.target.value) })}
                    className="w-full p-3 rounded-xl bg-zinc-900 border border-zinc-800 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-zinc-400 mb-2">Album Pack</label>
                  <input
                    type="number"
                    value={minPrices.album}
                    onChange={(e) => setMinPrices({ ...minPrices, album: Number(e.target.value) })}
                    className="w-full p-3 rounded-xl bg-zinc-900 border border-zinc-800 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-zinc-400 mb-2">Basic Subscription</label>
                  <input
                    type="number"
                    value={minPrices.subscription_basic}
                    onChange={(e) => setMinPrices({ ...minPrices, subscription_basic: Number(e.target.value) })}
                    className="w-full p-3 rounded-xl bg-zinc-900 border border-zinc-800 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-zinc-400 mb-2">Pro Subscription</label>
                  <input
                    type="number"
                    value={minPrices.subscription_pro}
                    onChange={(e) => setMinPrices({ ...minPrices, subscription_pro: Number(e.target.value) })}
                    className="w-full p-3 rounded-xl bg-zinc-900 border border-zinc-800 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-zinc-400 mb-2">Super Subscription</label>
                  <input
                    type="number"
                    value={minPrices.subscription_super}
                    onChange={(e) => setMinPrices({ ...minPrices, subscription_super: Number(e.target.value) })}
                    className="w-full p-3 rounded-xl bg-zinc-900 border border-zinc-800 text-white"
                  />
                </div>
              </div>

              <Button
                onClick={savePricing}
                disabled={saving}
                className="w-full mt-6"
              >
                {saving ? "Saving..." : "Save Pricing"}
              </Button>
            </motion.div>

            {/* Feature Flags Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="p-8 rounded-2xl bg-zinc-900/40 border border-zinc-800"
            >
              <div className="flex items-center gap-3 mb-6">
                <Flag className="text-amber-500" size={24} />
                <h2 className="text-2xl font-black text-white uppercase italic tracking-tight">
                  Feature Flags
                </h2>
              </div>

              <div className="space-y-4">
                {Object.entries(featureFlags).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between p-4 rounded-xl bg-zinc-900/40 border border-zinc-800">
                    <span className="text-white font-bold capitalize">
                      {key.replace(/_/g, " ")}
                    </span>
                    <button
                      onClick={() => setFeatureFlags({ ...featureFlags, [key]: !value })}
                      className={`px-4 py-2 rounded-lg font-bold transition-all ${
                        value
                          ? "bg-green-600 text-white"
                          : "bg-zinc-800 text-zinc-500"
                      }`}
                    >
                      {value ? "Enabled" : "Disabled"}
                    </button>
                  </div>
                ))}
              </div>

              <Button
                onClick={saveFeatureFlags}
                disabled={saving}
                className="w-full mt-6"
              >
                {saving ? "Saving..." : "Save Feature Flags"}
              </Button>
            </motion.div>
          </div>
        </div>
      </div>
    </RequireRole>
  );
}
