"use client";

import { useAuth } from "@/lib/AuthContext";
import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabaseClient";
import RequireRole from "@/components/features/auth/RequireRole";
import { Upload, Music, Package, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

export default function DJUploadPage() {
    const { user, loading: authLoading } = useAuth();

    const [file, setFile] = useState<File | null>(null);
    const [title, setTitle] = useState("");
    const [price, setPrice] = useState("");
    const [description, setDescription] = useState("");
    const [contentType, setContentType] = useState<"track" | "zip">("track");

    const [isUploading, setIsUploading] = useState(false);
    const [status, setStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0] || null;
        setFile(selectedFile);

        if (selectedFile) {
            const ext = selectedFile.name.split(".").pop()?.toLowerCase();
            if (["zip", "rar", "7z"].includes(ext || "")) {
                setContentType("zip");
            } else {
                setContentType("track");
            }
            if (!title) {
                setTitle(selectedFile.name.replace(/\.[^/.]+$/, ""));
            }
        }
    };

    const handleUpload = async (e: React.FormEvent) => {
        e.preventDefault();

        // Prevent duplicate submissions
        if (isUploading) {
            console.log("Upload already in progress, ignoring duplicate submission");
            return;
        }

        if (!file || !title || !price) {
            setStatus({ type: "error", message: "Please fill in all required fields." });
            return;
        }

        setIsUploading(true);
        setStatus(null);

        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) throw new Error("Authentication failed. Please login.");

            const formData = new FormData();
            formData.append("file", file);
            formData.append("title", title);
            formData.append("price", price);
            formData.append("description", description);
            formData.append("content_type", contentType);

            const res = await fetch("/api/dj/upload", {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${session.access_token}`,
                },
                body: formData,
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.error || "Upload failed");
            }

            setStatus({ type: "success", message: data.message || "Content uploaded and published successfully!" });
            setFile(null);
            setTitle("");
            setPrice("");
            setDescription("");
        } catch (err: any) {
            setStatus({ type: "error", message: err.message });
        } finally {
            setIsUploading(false);
        }
    };

    // Simple auth check
    if (authLoading) {
        return (
            <div className="min-h-screen bg-[#050505] flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
                    <p className="text-gray-400 animate-pulse">Loading...</p>
                </div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="min-h-screen bg-[#050505] flex items-center justify-center p-6">
                <div className="bg-white/5 border border-white/10 p-8 rounded-2xl max-w-sm text-center">
                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h2 className="text-xl font-bold mb-2">Login Required</h2>
                    <p className="text-gray-400 mb-6">You must be logged in to access the DJ upload portal.</p>
                    <a href="/login" className="bg-purple-600 px-6 py-2 rounded-lg font-bold">Log In</a>
                </div>
            </div>
        );
    }

    // RENDER UPLOAD FORM FOR ALL LOGGED IN USERS
    return (
        <div className="min-h-screen bg-[#050505] text-white p-6 md:p-12">
            <div className="max-w-3xl mx-auto">
                <div className="flex items-center gap-4 mb-8">
                    <div className="w-12 h-12 bg-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-purple-500/20">
                        <Upload className="w-6 h-6" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-500 bg-clip-text text-transparent">
                            Upload New Content
                        </h1>
                        <p className="text-gray-400 text-sm">Sell tracks or album packs to your fans.</p>
                    </div>
                </div>

                <form onSubmit={handleUpload} className="space-y-8">
                    {/* FILE DROPZONE */}
                    <div className={`relative border-2 border-dashed rounded-2xl p-8 transition-all ${file ? "border-purple-600 bg-purple-600/5" : "border-white/10 hover:border-white/20 bg-white/5"
                        }`}>
                        <input
                            type="file"
                            onChange={handleFileChange}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                        />
                        <div className="flex flex-col items-center text-center space-y-4">
                            <div className={`w-16 h-16 rounded-full flex items-center justify-center ${file ? "bg-purple-600" : "bg-white/10"
                                }`}>
                                {contentType === "zip" ? <Package className="w-8 h-8" /> : <Music className="w-8 h-8" />}
                            </div>
                            {file ? (
                                <div>
                                    <p className="text-lg font-semibold">{file.name}</p>
                                    <p className="text-sm text-purple-400">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                                </div>
                            ) : (
                                <div>
                                    <p className="text-lg font-semibold text-gray-300">Choose a file or drag & drop</p>
                                    <p className="text-sm text-gray-500 mt-1">MP3, WAV, WAV, or ZIP (Album Packs)</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* FORM FIELDS */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-400">Title</label>
                            <input
                                type="text"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder="e.g. Summer House Mix 2024"
                                className="w-full bg-white/5 border border-white/10 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-purple-600 transition-all font-medium"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-400">Price (₹)</label>
                            <div className="relative">
                                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500">₹</span>
                                <input
                                    type="number"
                                    value={price}
                                    onChange={(e) => setPrice(e.target.value)}
                                    placeholder="99"
                                    className="w-full bg-white/5 border border-white/10 rounded-xl p-3 pl-8 focus:outline-none focus:ring-2 focus:ring-purple-600 transition-all font-mono"
                                />
                            </div>
                        </div>

                        <div className="md:col-span-2 space-y-2">
                            <label className="text-sm font-medium text-gray-400">Description (Optional)</label>
                            <textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="Tell your fans about this release..."
                                rows={3}
                                className="w-full bg-white/5 border border-white/10 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-purple-600 transition-all"
                            />
                        </div>

                        <div className="md:col-span-2 space-y-2 font-medium">
                            <label className="text-sm font-medium text-gray-400">Content Type</label>
                            <div className="grid grid-cols-2 gap-4">
                                <button
                                    type="button"
                                    onClick={() => setContentType("track")}
                                    className={`p-3 rounded-xl border flex items-center justify-center gap-2 transition-all ${contentType === "track"
                                        ? "bg-purple-600 border-purple-600 text-white shadow-lg shadow-purple-600/20"
                                        : "bg-white/5 border-white/10 text-gray-400 hover:bg-white/10"
                                        }`}
                                >
                                    <Music className="w-4 h-4" /> Single Track
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setContentType("zip")}
                                    className={`p-3 rounded-xl border flex items-center justify-center gap-2 transition-all ${contentType === "zip"
                                        ? "bg-purple-600 border-purple-600 text-white shadow-lg shadow-purple-600/20"
                                        : "bg-white/5 border-white/10 text-gray-400 hover:bg-white/10"
                                        }`}
                                >
                                    <Package className="w-4 h-4" /> Album Pack (ZIP)
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* STATUS MESSAGES */}
                    {status && (
                        <div className={`p-4 rounded-xl flex items-center gap-3 animate-in fade-in slide-in-from-top-2 ${status.type === "success" ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
                            }`}>
                            {status.type === "success" ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
                            <p className="text-sm font-medium">{status.message}</p>
                        </div>
                    )}

                    {/* SUBMIT BUTTON */}
                    <button
                        type="submit"
                        disabled={isUploading}
                        className={`w-full py-4 rounded-2xl font-bold text-lg flex items-center justify-center gap-3 transition-all ${isUploading
                            ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                            : "bg-purple-600 text-white hover:bg-purple-500 shadow-xl shadow-purple-600/20 active:scale-[0.98]"
                            }`}
                    >
                        {isUploading ? (
                            <>
                                <Loader2 className="w-6 h-6 animate-spin" />
                                Uploading & Publishing...
                            </>
                        ) : (
                            <>
                                <Upload className="w-6 h-6" />
                                Publish Now
                            </>
                        )}
                    </button>
                </form>

                <div className="mt-12 pt-8 border-t border-white/10">
                    <h3 className="text-gray-400 text-xs font-bold uppercase tracking-widest mb-4">Upload Guidelines</h3>
                    <ul className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-gray-500">
                        <li className="flex items-center gap-2">
                            <div className="w-1.5 h-1.5 bg-purple-600 rounded-full" />
                            Audio files must be MP3, WAV or FLAC.
                        </li>
                        <li className="flex items-center gap-2">
                            <div className="w-1.5 h-1.5 bg-purple-600 rounded-full" />
                            Album packs must be in .zip format.
                        </li>
                        <li className="flex items-center gap-2">
                            <div className="w-1.5 h-1.5 bg-purple-600 rounded-full" />
                            Maximum file size is currently 50MB.
                        </li>
                        <li className="flex items-center gap-2">
                            <div className="w-1.5 h-1.5 bg-purple-600 rounded-full" />
                            Ensure you hold all rights to the content.
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    );
}
