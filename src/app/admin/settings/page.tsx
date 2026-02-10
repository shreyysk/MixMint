'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import RequireRole from "@/components/features/auth/RequireRole";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/Button";
import {
  Settings,
  Shield,
  Mail,
  CreditCard,
  Terminal,
  Globe,
  Save,
  RotateCw,
  Lock
} from 'lucide-react';

export default function PlatformSettingsPage() {
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  const [settings, setSettings] = useState({
    platformName: 'MixMint',
    commissionPercent: 15,
    tokenExpiryMinutes: 5,
    maxUploadMB: 500,
    supportEmail: 'support@mixmint.com',
    isMaintenanceMode: false
  });

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    try {
      setLoading(true);
      const { data, error } = await supabase
        .from('system_settings')
        .select('*');

      if (error) throw error;

      const newSettings = { ...settings };
      data?.forEach(s => {
        if (s.key === 'platform_config') {
          Object.assign(newSettings, s.value);
        } else if (s.key === 'maintenance_mode') {
          newSettings.isMaintenanceMode = s.value.enabled;
        }
      });
      setSettings(newSettings);
    } catch (err) {
      console.error('[LOAD_SETTINGS_ERROR]', err);
    } finally {
      setLoading(false);
    }
  }

  const handleSave = async () => {
    setSaving(true);
    try {
      // 1. Save Platform Config
      const { error: configErr } = await supabase
        .from('system_settings')
        .upsert({
          key: 'platform_config',
          value: {
            platformName: settings.platformName,
            commissionPercent: settings.commissionPercent,
            tokenExpiryMinutes: settings.tokenExpiryMinutes,
            maxUploadMB: settings.maxUploadMB,
            supportEmail: settings.supportEmail
          },
          updated_at: new Date().toISOString()
        });

      if (configErr) throw configErr;

      // 2. Save Maintenance Mode
      const { error: maintErr } = await supabase
        .from('system_settings')
        .upsert({
          key: 'maintenance_mode',
          value: { enabled: settings.isMaintenanceMode },
          updated_at: new Date().toISOString()
        });

      if (maintErr) throw maintErr;

      alert('Settings saved successfully to the database!');
    } catch (err) {
      console.error('[SAVE_SETTINGS_ERROR]', err);
      alert('Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <RequireRole allowed={["admin"]}>
      <div className="p-6 space-y-8 animate-in fade-in duration-500">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-zinc-800 rounded-2xl border border-zinc-700">
              <Settings className="w-8 h-8 text-zinc-400" />
            </div>
            <div>
              <h1 className="text-3xl font-heading font-bold text-white">Platform Settings</h1>
              <p className="text-zinc-400">Configure global platform behavior and thresholds.</p>
            </div>
          </div>
          <Button
            onClick={handleSave}
            disabled={saving || loading}
            className="bg-purple-600 hover:bg-purple-500 text-white rounded-xl shadow-purple-glow gap-2 px-8"
          >
            {saving ? <RotateCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* General Settings */}
          <Card className="bg-zinc-950/50 border-zinc-900">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Globe className="w-5 h-5 text-blue-400" />
                General Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest block">Platform Name</label>
                <input
                  type="text"
                  value={settings.platformName}
                  onChange={(e) => setSettings({ ...settings, platformName: e.target.value })}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest block">Support Contact Email</label>
                <input
                  type="email"
                  value={settings.supportEmail}
                  onChange={(e) => setSettings({ ...settings, supportEmail: e.target.value })}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50"
                />
              </div>
            </CardContent>
          </Card>

          {/* Financial & Monetization */}
          <Card className="bg-zinc-950/50 border-zinc-900">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-emerald-400" />
                Monetization Thresholds
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest block">Platform Commission (%)</label>
                <input
                  type="number"
                  value={settings.commissionPercent}
                  onChange={(e) => setSettings({ ...settings, commissionPercent: parseInt(e.target.value) })}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50"
                />
              </div>
              <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-2xl flex items-start gap-3">
                <Terminal className="w-5 h-5 text-emerald-500 mt-1" />
                <p className="text-xs text-emerald-200/60 leading-relaxed font-medium">
                  This rate is applied globally to all purchases and subscriptions unless a custom override is set per DJ.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Security & Token Settings */}
          <Card className="bg-zinc-950/50 border-zinc-900">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Shield className="w-5 h-5 text-purple-400" />
                Security & Token Policy
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest block">Download Token Expiry (Minutes)</label>
                <input
                  type="number"
                  value={settings.tokenExpiryMinutes}
                  onChange={(e) => setSettings({ ...settings, tokenExpiryMinutes: parseInt(e.target.value) })}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest block">Max Upload File Size (MB)</label>
                <input
                  type="number"
                  value={settings.maxUploadMB}
                  onChange={(e) => setSettings({ ...settings, maxUploadMB: parseInt(e.target.value) })}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50"
                />
              </div>
            </CardContent>
          </Card>

          {/* System Maintenance */}
          <Card className="bg-zinc-950/50 border-red-500/10 hover:border-red-500/30 transition-all border-dashed">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Lock className="w-5 h-5 text-red-500" />
                System Overrides
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between p-4 bg-red-500/5 border border-red-500/10 rounded-2xl">
                <div>
                  <h4 className="text-sm font-bold text-white">Maintenance Mode</h4>
                  <p className="text-[10px] text-red-300/50 font-medium uppercase tracking-widest">Blocks all public access except for Admins.</p>
                </div>
                <button
                  onClick={() => setSettings({ ...settings, isMaintenanceMode: !settings.isMaintenanceMode })}
                  className={`w-12 h-6 rounded-full transition-all relative ${settings.isMaintenanceMode ? 'bg-red-600 shadow-red-glow' : 'bg-zinc-800'}`}
                >
                  <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${settings.isMaintenanceMode ? 'left-7' : 'left-1'}`} />
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </RequireRole>
  );
}
