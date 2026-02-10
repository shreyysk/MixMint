"use client";

import { useAuth } from "@/lib/AuthContext";
import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabaseClient";
import {
    Upload, Music, Package, CheckCircle2, AlertCircle,
    Loader2, Plus, Trash2, ArrowRight, Save, Play,
    Layers, ChevronRight, Info
} from "lucide-react";
import { useRouter } from "next/navigation";

type UploadMode = "track" | "album_gen" | "album_zip";

export default function DJUploadPage() {
    const { user, loading: authLoading } = useAuth();
    const router = useRouter();

    // 1. Wizard State
    const [mode, setMode] = useState<UploadMode | null>(null);
    const [step, setStep] = useState(1); // 1: Select Mode, 2: Upload logic

    // 2. Common Metadata
    const [title, setTitle] = useState("");
    const [price, setPrice] = useState("");
    const [description, setDescription] = useState("");
    const [isFanOnly, setIsFanOnly] = useState(false);

    // 3. Mode-Specific Data
    // Single Track / Direct ZIP
    const [mainFile, setMainFile] = useState<File | null>(null);

    // Album Gen (Multi-track)
    const [albumTracks, setAlbumTracks] = useState<{ id: string; file: File; title: string; order: number }[]>([]);
    const [isFinalizing, setIsFinalizing] = useState(false);
    const [activeAlbumId, setActiveAlbumId] = useState<string | null>(null);

    // 4. UI Status
    const [isUploading, setIsUploading] = useState(false);
    const [status, setStatus] = useState<{ type: "success" | "error" | "info"; message: string } | null>(null);

    // ==========================================
    // ACTIONS
    // ==========================================

    const resetForm = () => {
        setMode(null);
        setStep(1);
        setMainFile(null);
        setAlbumTracks([]);
        setTitle("");
        setPrice("");
        setDescription("");
        setIsFanOnly(false);
        setActiveAlbumId(null);
        setStatus(null);
    };

    const handleSingleUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!mainFile || !title || !price) {
            setStatus({ type: "error", message: "Please fill in all required fields." });
            return;
        }

        setIsUploading(true);
        setStatus({ type: "info", message: "Uploading to secure storage..." });

        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) throw new Error("Session expired. Please re-login.");

            const formData = new FormData();
            formData.append("file", mainFile);
            formData.append("title", title);
            formData.append("price", price);
            formData.append("description", description);
            formData.append("is_fan_only", String(isFanOnly));

            // Use appropriate API
            const endpoint = mode === "track" ? "/api/dj/tracks/upload" : "/api/dj/albums/upload";
            if (mode === "album_zip") formData.append("upload_method", "direct_zip");

            const res = await fetch(endpoint, {
                method: "POST",
                headers: { Authorization: `Bearer ${session.access_token}` },
                body: formData,
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Upload failed");

            setStatus({
                type: "success",
                message: mode === "album_zip"
                    ? "ZIP uploaded! Background metadata injection started."
                    : "Published successfully!"
            });

            // Redirect or show success
            setTimeout(() => {
                if (mode === "track") router.push("/dj/tracks");
                else router.push("/dj/albums");
            }, 2000);

        } catch (err: any) {
            console.error(err);
            setStatus({ type: "error", message: err.message });
            setIsUploading(false);
        }
    };

    const startAlbumGen = async () => {
        if (!title || !price) {
            setStatus({ type: "error", message: "Album title and price required to start session." });
            return;
        }

        setIsUploading(true);
        try {
            const { data: { session } } = await supabase.auth.getSession();
            const formData = new FormData();
            // Just metadata first
            formData.append("title", title);
            formData.append("price", price);
            formData.append("description", description);
            formData.append("is_fan_only", String(isFanOnly));
            formData.append("upload_method", "system_generated");
            formData.append("file", new Blob(["session_init"], { type: 'text/plain' }), "init.txt"); // Placeholder for the required file field in backend

            const res = await fetch("/api/dj/albums/upload", {
                method: "POST",
                headers: { Authorization: `Bearer ${session?.access_token}` },
                body: formData,
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Failed to initialize album session");

            setActiveAlbumId(data.albumId);
            setStep(3); // Go to track upload
            setStatus({ type: "success", message: "Album session created. Start adding tracks!" });
        } catch (err: any) {
            setStatus({ type: "error", message: err.message });
        } finally {
            setIsUploading(false);
        }
    };

    const addTrackToAlbum = async (file: File) => {
        if (!activeAlbumId) return;

        const trackId = Math.random().toString(36).substr(2, 9);
        const newTrack = { id: trackId, file, title: file.name.replace(/\.[^/.]+$/, ""), order: albumTracks.length + 1 };
        setAlbumTracks(prev => [...prev, newTrack]);

        // Auto-upload track to temp storage
        try {
            const { data: { session } } = await supabase.auth.getSession();
            const formData = new FormData();
            formData.append("file", file);
            formData.append("title", newTrack.title);
            formData.append("order", String(newTrack.order));

            const res = await fetch(`/api/dj/albums/${activeAlbumId}/tracks`, {
                method: "POST",
                headers: { Authorization: `Bearer ${session?.access_token}` },
                body: formData,
            });

            if (!res.ok) throw new Error("Track upload failed");
            console.log(`Track ${newTrack.title} uploaded to temp`);
        } catch (err) {
            console.error(err);
            setStatus({ type: "error", message: "Wait! One of the tracks failed to upload to temp storage." });
        }
    };

    const finalizeAlbum = async () => {
        if (albumTracks.length === 0) return;
        setIsFinalizing(true);
        try {
            const { data: { session } } = await supabase.auth.getSession();
            const res = await fetch(`/api/dj/albums/${activeAlbumId}/tracks`, {
                method: "PATCH",
                headers: { Authorization: `Bearer ${session?.access_token}` }
            });

            if (!res.ok) throw new Error("Finalization failed");

            setStatus({ type: "success", message: "Album finalized! Our system is now generating your professional ZIP." });
            setTimeout(() => router.push("/dj/albums"), 3000);
        } catch (err: any) {
            setStatus({ type: "error", message: err.message });
            setIsFinalizing(false);
        }
    };

    // ==========================================
    // RENDER HELPERS
    // ==========================================

    if (authLoading) return <LoadingScreen />;
    if (!user) return <AuthRequiredScreen />;

    return (
        <div className="min-h-screen bg-[#050505] text-white p-6 md:p-12 font-sans selection:bg-purple-600/30">
            <div className="max-w-4xl mx-auto">
                <Header step={step} reset={resetForm} />

                {/* STEP 1: SELECT MODE */}
                {step === 1 && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <ModeCard
                            icon={<Music className="w-8 h-8" />}
                            title="Single Track"
                            desc="Upload a single MP3/WAV with custom price and cover art."
                            onClick={() => { setMode("track"); setStep(2); }}
                        />
                        <ModeCard
                            icon={<Layers className="w-8 h-8" />}
                            title="Multi-Track Album"
                            desc="Add individual tracks one-by-one. We'll generate a professional ZIP for you."
                            onClick={() => { setMode("album_gen"); setStep(2); }}
                            highlight
                        />
                        <ModeCard
                            icon={<Package className="w-8 h-8" />}
                            title="Pre-made ZIP"
                            desc="Already have a ZIP? We'll unpack, watermark, and repack it for you."
                            onClick={() => { setMode("album_zip"); setStep(2); }}
                        />
                    </div>
                )}

                {/* STEP 2: METADATA & MAIN ACTION */}
                {step === 2 && (
                    <div className="space-y-8 animate-in fade-in duration-300">
                        <MetadataForm
                            title={title} setTitle={setTitle}
                            price={price} setPrice={setPrice}
                            desc={description} setDesc={setDescription}
                            isFanOnly={isFanOnly} setIsFanOnly={setIsFanOnly}
                            mode={mode!}
                        />

                        {(mode === "track" || mode === "album_zip") ? (
                            <form onSubmit={handleSingleUpload} className="space-y-6">
                                <Dropzone
                                    file={mainFile}
                                    setFile={setMainFile}
                                    accept={mode === "track" ? "audio/*" : ".zip,.rar,.7z"}
                                />
                                <StatusMessage status={status} />
                                <button
                                    type="submit"
                                    disabled={isUploading}
                                    className="w-full h-16 bg-purple-600 hover:bg-purple-500 rounded-2xl font-bold text-lg flex items-center justify-center gap-3 transition-all active:scale-[0.98] disabled:bg-gray-800 disabled:text-gray-500 shadow-xl shadow-purple-600/20"
                                >
                                    {isUploading ? <Loader2 className="animate-spin" /> : <Upload />}
                                    {isUploading ? "Uploading..." : `Publish ${mode === "track" ? "Track" : "Album"}`}
                                </button>
                            </form>
                        ) : (
                            <div className="space-y-6">
                                <StatusMessage status={status} />
                                <button
                                    onClick={startAlbumGen}
                                    disabled={isUploading}
                                    className="w-full h-16 bg-white text-black hover:bg-gray-200 rounded-2xl font-bold text-lg flex items-center justify-center gap-3 transition-all active:scale-[0.98]"
                                >
                                    {isUploading ? <Loader2 className="animate-spin text-purple-600" /> : <ArrowRight />}
                                    Create Album Session
                                </button>
                            </div>
                        )}
                    </div>
                )}

                {/* STEP 3: TRACK BUILDER (ALBUM GEN) */}
                {step === 3 && (
                    <div className="space-y-8 animate-in zoom-in-95 duration-300">
                        <div className="bg-white/5 border border-white/10 p-6 rounded-3xl">
                            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                                <Music className="text-purple-500" /> Tracklist for "{title}"
                            </h2>
                            <div className="space-y-3">
                                {albumTracks.map((t, i) => (
                                    <div key={t.id} className="flex items-center gap-4 bg-black/40 p-4 rounded-2xl border border-white/5 group">
                                        <div className="w-10 h-10 bg-white/5 rounded-lg flex items-center justify-center text-gray-500 font-mono text-sm">
                                            {i + 1}
                                        </div>
                                        <div className="flex-1">
                                            <p className="font-semibold">{t.title}</p>
                                            <p className="text-xs text-gray-500 uppercase tracking-tighter">{(t.file.size / (1024 * 1024)).toFixed(2)} MB • READY</p>
                                        </div>
                                        <button
                                            onClick={() => setAlbumTracks(prev => prev.filter(x => x.id !== t.id))}
                                            className="p-2 hover:bg-red-500/10 text-gray-500 hover:text-red-500 rounded-xl transition-colors opacity-0 group-hover:opacity-100"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                ))}
                                <label className="flex flex-col items-center justify-center border-2 border-dashed border-white/10 hover:border-purple-500/50 p-6 rounded-2xl cursor-pointer transition-colors bg-white/2 hover:bg-white/5">
                                    <input
                                        type="file"
                                        className="hidden"
                                        accept="audio/*"
                                        onChange={(e) => e.target.files?.[0] && addTrackToAlbum(e.target.files[0])}
                                    />
                                    <div className="w-10 h-10 bg-purple-600/20 text-purple-400 rounded-full flex items-center justify-center mb-2">
                                        <Plus className="w-6 h-6" />
                                    </div>
                                    <p className="text-sm font-medium text-gray-400">Add Track</p>
                                </label>
                            </div>
                        </div>

                        <div className="bg-purple-600/10 border border-purple-500/20 p-4 rounded-2xl flex items-start gap-3">
                            <Info className="text-purple-500 w-5 h-5 flex-shrink-0 mt-0.5" />
                            <p className="text-sm text-purple-300">MixMint will automatically add your DJ name, Album Title, and custom watermarks to each track when generating the final ZIP.</p>
                        </div>

                        <StatusMessage status={status} />

                        <button
                            onClick={finalizeAlbum}
                            disabled={isFinalizing || albumTracks.length === 0}
                            className="w-full h-16 bg-purple-600 hover:bg-purple-500 rounded-2xl font-bold text-lg flex items-center justify-center gap-3 transition-all active:scale-[0.98] disabled:bg-gray-800 disabled:text-gray-500 shadow-xl shadow-purple-600/40"
                        >
                            {isFinalizing ? <Loader2 className="animate-spin" /> : <Save />}
                            {isFinalizing ? "Finalizing Package..." : "Finalize & Generate ZIP"}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

// ==========================================
// SUB-COMPONENTS
// ==========================================

function Header({ step, reset }: { step: number; reset: () => void }) {
    return (
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <div className="px-3 py-1 bg-purple-600/10 text-purple-500 text-[10px] font-bold uppercase tracking-widest border border-purple-600/20 rounded-full">
                        Step {step} of 3
                    </div>
                </div>
                <h1 className="text-4xl md:text-5xl font-black bg-gradient-to-br from-white via-white to-gray-500 bg-clip-text text-transparent">
                    {step === 1 ? "Start New Release" : step === 2 ? "Meta & Packaging" : "Tracklist Builder"}
                </h1>
                <p className="text-gray-500 mt-2 font-medium">Sell your music directly to your fans with professional processing.</p>
            </div>
            {step > 1 && (
                <button
                    onClick={reset}
                    className="px-6 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-sm font-bold transition-all"
                >
                    Cancel & Restart
                </button>
            )}
        </div>
    );
}

function ModeCard({ icon, title, desc, onClick, highlight = false }: any) {
    return (
        <button
            onClick={onClick}
            className={`flex flex-col items-start p-8 rounded-[2rem] border transition-all text-left h-full group ${highlight
                    ? "bg-purple-600 shadow-2xl shadow-purple-600/20 border-purple-500 hover:-translate-y-2 ring-4 ring-purple-600/10"
                    : "bg-white/5 border-white/10 hover:border-white/20 hover:bg-white/10 hover:-translate-y-1"
                }`}
        >
            <div className={`p-4 rounded-2xl mb-6 transition-transform group-hover:scale-110 ${highlight ? "bg-white text-purple-600" : "bg-purple-600/20 text-purple-500"}`}>
                {icon}
            </div>
            <h3 className="text-xl font-bold mb-2 group-hover:tracking-tight transition-all">{title}</h3>
            <p className={`text-sm leading-relaxed ${highlight ? "text-purple-100" : "text-gray-500"}`}>{desc}</p>
            <div className={`mt-8 flex items-center gap-2 text-sm font-bold ${highlight ? "text-white" : "text-purple-500"}`}>
                Get Started <ChevronRight className="w-4 h-4" />
            </div>
        </button>
    );
}

function MetadataForm({ title, setTitle, price, setPrice, desc, setDesc, isFanOnly, setIsFanOnly, mode }: any) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-white/5 border border-white/10 p-8 rounded-[2.5rem]">
            <div className="space-y-2">
                <label className="text-xs font-bold text-gray-500 uppercase tracking-widest pl-1">Release Title</label>
                <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Summer House Mix 2024"
                    className="w-full bg-black/40 border border-white/10 rounded-2xl p-4 focus:outline-none focus:ring-2 focus:ring-purple-600 transition-all font-semibold"
                />
            </div>

            <div className="space-y-2">
                <label className="text-xs font-bold text-gray-500 uppercase tracking-widest pl-1">Price (₹)</label>
                <div className="relative">
                    <span className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-500 font-bold">₹</span>
                    <input
                        type="number"
                        value={price}
                        onChange={(e) => setPrice(e.target.value)}
                        placeholder={mode === "track" ? "29" : "79"}
                        className="w-full bg-black/40 border border-white/10 rounded-2xl p-4 pl-10 focus:outline-none focus:ring-2 focus:ring-purple-600 transition-all font-mono font-bold"
                    />
                </div>
            </div>

            <div className="md:col-span-2 space-y-2">
                <label className="text-xs font-bold text-gray-500 uppercase tracking-widest pl-1">Description</label>
                <textarea
                    value={desc}
                    onChange={(e) => setDesc(e.target.value)}
                    placeholder="Tell your fans about this release..."
                    rows={3}
                    className="w-full bg-black/40 border border-white/10 rounded-2xl p-4 focus:outline-none focus:ring-2 focus:ring-purple-600 transition-all"
                />
            </div>

            <div className="md:col-span-2 flex items-center gap-3 p-4 bg-black/20 rounded-2xl border border-white/5">
                <input
                    type="checkbox"
                    checked={isFanOnly}
                    onChange={(e) => setIsFanOnly(e.target.checked)}
                    className="w-5 h-5 rounded border-white/10 bg-white/5 text-purple-600 focus:ring-purple-600 cursor-pointer"
                />
                <div className="flex-1">
                    <p className="text-sm font-bold">Fan-Only Content</p>
                    <p className="text-[10px] text-gray-500 uppercase tracking-widest font-black">Exclusive to your subscribers</p>
                </div>
            </div>
        </div>
    );
}

function Dropzone({ file, setFile, accept }: any) {
    return (
        <div className={`relative border-2 border-dashed rounded-[2rem] p-12 transition-all group ${file ? "border-purple-600 bg-purple-600/5 ring-8 ring-purple-600/5" : "border-white/10 hover:border-white/30 bg-white/5"
            }`}>
            <input
                type="file"
                accept={accept}
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
            />
            <div className="flex flex-col items-center text-center space-y-4">
                <div className={`w-20 h-20 rounded-[1.5rem] flex items-center justify-center transition-transform group-hover:scale-110 ${file ? "bg-purple-600 shadow-xl shadow-purple-600/40" : "bg-white/10"
                    }`}>
                    <Upload className="w-10 h-10" />
                </div>
                {file ? (
                    <div>
                        <p className="text-xl font-black mb-1">{file.name}</p>
                        <p className="text-sm text-purple-400 font-bold uppercase tracking-tighter">{(file.size / (1024 * 1024)).toFixed(2)} MB • READY TO SHIP</p>
                    </div>
                ) : (
                    <div>
                        <p className="text-xl font-bold text-gray-300">Drop your file here</p>
                        <p className="text-sm text-gray-500 mt-2 font-medium">Click to browse your device</p>
                    </div>
                )}
            </div>
        </div>
    );
}

function StatusMessage({ status }: any) {
    if (!status) return null;
    const styles = {
        success: "bg-green-500/10 text-green-400 border-green-500/20",
        error: "bg-red-500/10 text-red-400 border-red-500/20",
        info: "bg-purple-500/10 text-purple-400 border-purple-500/20"
    };
    return (
        <div className={`p-5 rounded-2xl flex items-center gap-4 border animate-in slide-in-from-top-4 ${styles[status.type as keyof typeof styles]}`}>
            {status.type === "success" ? <CheckCircle2 className="flex-shrink-0" /> : <AlertCircle className="flex-shrink-0" />}
            <p className="text-sm font-bold tracking-tight">{status.message}</p>
        </div>
    );
}

function LoadingScreen() {
    return (
        <div className="min-h-screen bg-[#050505] flex items-center justify-center">
            <div className="flex flex-col items-center gap-6">
                <div className="relative">
                    <div className="w-16 h-16 border-4 border-purple-600/20 rounded-full" />
                    <div className="w-16 h-16 border-4 border-t-purple-600 rounded-full animate-spin absolute inset-0" />
                </div>
                <p className="text-gray-500 font-bold uppercase tracking-[0.3em] text-xs animate-pulse">Initializing Portal</p>
            </div>
        </div>
    );
}

function AuthRequiredScreen() {
    return (
        <div className="min-h-screen bg-[#050505] flex items-center justify-center p-6">
            <div className="bg-white/5 border border-white/10 p-12 rounded-[3rem] max-w-md text-center backdrop-blur-xl">
                <div className="w-20 h-20 bg-red-500/10 text-red-500 rounded-3xl flex items-center justify-center mx-auto mb-8">
                    <AlertCircle className="w-10 h-10" />
                </div>
                <h2 className="text-3xl font-black mb-4">Access Denied</h2>
                <p className="text-gray-400 mb-10 leading-relaxed">You need an active DJ session to access the MixMint upload infrastructure.</p>
                <a href="/login" className="block w-full bg-white text-black py-4 rounded-2xl font-black hover:scale-[1.02] transition-transform">Log In to Portal</a>
            </div>
        </div>
    );
}
