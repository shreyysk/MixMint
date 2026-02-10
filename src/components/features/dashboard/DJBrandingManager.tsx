'use client';

import React, { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/lib/AuthContext';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Palette, Globe, Upload, Save, Layout, Type } from 'lucide-react';

export function DJBrandingManager() {
    const { user } = useAuth();
    const [settings, setSettings] = useState({
        custom_domain: '',
        custom_css: '',
        logo_url: '',
        banner_url: '',
        color_scheme: { primary: '#7c3aed', secondary: '#a78bfa' },
        fonts: { heading: 'Inter', body: 'Inter' }
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (user) loadBranding();
    }, [user]);

    async function loadBranding() {
        try {
            const { data, error } = await supabase
                .from('dj_branding')
                .select('*')
                .eq('dj_id', user?.id)
                .single();

            if (data) setSettings(data);
        } catch (err) {
            console.error('[LOAD_BRANDING_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    async function handleSave() {
        if (!user) return;
        try {
            setSaving(true);
            const { error } = await supabase
                .from('dj_branding')
                .upsert({
                    dj_id: user.id,
                    ...settings,
                    updated_at: new Date().toISOString()
                });

            if (error) throw error;
        } catch (err) {
            console.error('[SAVE_BRANDING_ERROR]', err);
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-heading font-bold text-white flex items-center gap-3">
                        <Palette className="w-7 h-7 text-purple-400" />
                        DJ Branding & Customization
                    </h2>
                    <p className="text-zinc-400">Personalize your storefront and stand out from the crowd.</p>
                </div>
                <Button
                    onClick={handleSave}
                    disabled={saving}
                    className="bg-purple-600 hover:bg-purple-500 text-white gap-2 rounded-xl shadow-purple-glow"
                >
                    <Save className="w-4 h-4" />
                    {saving ? 'Saving...' : 'Save Changes'}
                </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Visual Identity */}
                <Card className="bg-zinc-950/50 border-zinc-800">
                    <CardHeader>
                        <CardTitle className="text-white flex items-center gap-2">
                            <Layout className="w-5 h-5 text-purple-400" />
                            Visual Identity
                        </CardTitle>
                        <CardDescription>Custom logos, banners, and themes.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest block">Primary Color</label>
                                <div className="flex gap-2">
                                    <input
                                        type="color"
                                        value={settings.color_scheme.primary}
                                        onChange={(e) => setSettings({ ...settings, color_scheme: { ...settings.color_scheme, primary: e.target.value } })}
                                        className="w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-800 cursor-pointer"
                                    />
                                    <input
                                        type="text"
                                        value={settings.color_scheme.primary}
                                        onChange={(e) => setSettings({ ...settings, color_scheme: { ...settings.color_scheme, primary: e.target.value } })}
                                        className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-3 text-sm text-zinc-300 focus:outline-none"
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest block">Secondary Color</label>
                                <div className="flex gap-2">
                                    <input
                                        type="color"
                                        value={settings.color_scheme.secondary}
                                        onChange={(e) => setSettings({ ...settings, color_scheme: { ...settings.color_scheme, secondary: e.target.value } })}
                                        className="w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-800 cursor-pointer"
                                    />
                                    <input
                                        type="text"
                                        value={settings.color_scheme.secondary}
                                        onChange={(e) => setSettings({ ...settings, color_scheme: { ...settings.color_scheme, secondary: e.target.value } })}
                                        className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-3 text-sm text-zinc-300 focus:outline-none"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <div className="p-4 border border-dashed border-zinc-800 rounded-2xl bg-zinc-900/30 text-center">
                                <Upload className="w-8 h-8 text-zinc-700 mx-auto mb-2" />
                                <p className="text-xs text-zinc-500">Upload Storefront Banner (1920x400)</p>
                            </div>
                            <div className="p-4 border border-dashed border-zinc-800 rounded-2xl bg-zinc-900/30 text-center">
                                <Upload className="w-8 h-8 text-zinc-700 mx-auto mb-2" />
                                <p className="text-xs text-zinc-500">Upload Logo (512x512)</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Domain & CSS */}
                <Card className="bg-zinc-950/50 border-zinc-800">
                    <CardHeader>
                        <CardTitle className="text-white flex items-center gap-2">
                            <Globe className="w-5 h-5 text-blue-400" />
                            Advanced Setup
                        </CardTitle>
                        <CardDescription>Custom domains and advanced CSS injection.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest block">Custom Domain (CNAME)</label>
                            <input
                                type="text"
                                value={settings.custom_domain}
                                onChange={(e) => setSettings({ ...settings, custom_domain: e.target.value })}
                                placeholder="music.yourname.com"
                                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 transition-all shadow-inner"
                            />
                            <p className="text-[10px] text-zinc-600">Point your CNAME to mixmint.site to use your own domain.</p>
                        </div>

                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest block">Custom CSS (Pro Only)</label>
                            <textarea
                                value={settings.custom_css}
                                onChange={(e) => setSettings({ ...settings, custom_css: e.target.value })}
                                placeholder=".hero-banner { filter: blur(10px); }"
                                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-zinc-400 font-mono focus:outline-none focus:border-purple-500 transition-all h-32"
                            />
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
