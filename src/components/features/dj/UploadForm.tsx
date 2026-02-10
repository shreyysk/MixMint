"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Music, Package, Upload, Check, X } from "lucide-react";

interface UploadFormProps {
    type: 'track' | 'album';
    onSuccess: () => void;
}

export function UploadForm({ type, onSuccess }: UploadFormProps) {
    const [file, setFile] = useState<File | null>(null);
    const [title, setTitle] = useState("");
    const [price, setPrice] = useState<number>(0);
    const [isFree, setIsFree] = useState(false);
    const [description, setDescription] = useState("");
    const [youtubeUrl, setYoutubeUrl] = useState("");
    const [bpm, setBpm] = useState<number | "">("");
    const [genre, setGenre] = useState("");
    const [coverFile, setCoverFile] = useState<File | null>(null);
    const [coverPreview, setCoverPreview] = useState<string | null>(null);
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    const isTrack = type === 'track';
    const maxSize = isTrack ? 300 * 1024 * 1024 : 1000 * 1024 * 1024; // 300MB for tracks (High-Res), 1GB for albums
    const acceptedTypes = isTrack
        ? '.mp3,.wav,.flac,.m4a,.aac'
        : '.zip,.rar,.7z';

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (!selectedFile) return;

        // Validate file size
        if (selectedFile.size > maxSize) {
            setError(`File too large. Max size: ${isTrack ? '300MB' : '1GB'}`);
            return;
        }

        // Validate file type
        const ext = selectedFile.name.split('.').pop()?.toLowerCase();
        const validExts = isTrack
            ? ['mp3', 'wav', 'flac', 'm4a', 'aac']
            : ['zip', 'rar', '7z'];

        if (!ext || !validExts.includes(ext)) {
            setError(`Invalid file type. Accepted: ${acceptedTypes}`);
            return;
        }

        setFile(selectedFile);
        setError(null);

        // Metadata Extraction
        if (isTrack) {
            try {
                setIsAnalyzing(true);
                // Dynamic import to avoid SSR issues with buffer/stream
                const { parseBlob } = await import('music-metadata-browser');
                const metadata = await parseBlob(selectedFile);

                // Auto-fill Title if empty or matches filename pattern
                if (!title) {
                    // removing extension and underscores
                    const cleanName = selectedFile.name.replace(/\.[^/.]+$/, "").replace(/_/g, " ");
                    setTitle(metadata.common.title || cleanName);
                }

                // Auto-fill BPM
                if (metadata.common.bpm) {
                    setBpm(Math.round(metadata.common.bpm));
                }

                // Auto-fill Genre
                if (metadata.common.genre && metadata.common.genre.length > 0) {
                    setGenre(metadata.common.genre[0]);
                }

            } catch (err) {
                console.warn("Failed to extract metadata:", err);
                // Fallback: just use filename for title
                if (!title) {
                    const cleanName = selectedFile.name.replace(/\.[^/.]+$/, "").replace(/_/g, " ");
                    setTitle(cleanName);
                }
            } finally {
                setIsAnalyzing(false);
            }
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!file || !title) {
            setError("Please fill in all required fields");
            return;
        }

        if (!isFree && price <= 0) {
            setError("Please set a price or mark as free");
            return;
        }

        try {
            setUploading(true);
            setError(null);
            setProgress(0);

            const formData = new FormData();
            formData.append('file', file);
            formData.append('title', title);
            formData.append('price', isFree ? '0' : price.toString());
            formData.append('content_type', isTrack ? 'track' : 'zip');

            if (description) {
                formData.append('description', description);
            }

            if (isTrack) {
                if (bpm) formData.append('bpm', bpm.toString());
                if (genre) formData.append('genre', genre);
                if (youtubeUrl) formData.append('youtube_url', youtubeUrl);
                if (coverFile) formData.append('cover_file', coverFile);
            }

            // Simulate progress (since we can't track actual upload progress easily)
            const progressInterval = setInterval(() => {
                setProgress(prev => Math.min(prev + 10, 90));
            }, 200);

            const res = await fetch('/api/dj/upload', {
                method: 'POST',
                body: formData,
            });

            clearInterval(progressInterval);
            setProgress(100);

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.error || 'Upload failed');
            }

            // Success!
            setSuccess(true);
            setTimeout(() => {
                resetForm();
                onSuccess();
            }, 2000);

        } catch (err: any) {
            console.error('[UPLOAD_ERROR]', err);
            setError(err.message || 'Upload failed. Please try again.');
            setProgress(0);
        } finally {
            setUploading(false);
        }
    };

    const resetForm = () => {
        setFile(null);
        setTitle("");
        setPrice(0);
        setIsFree(false);
        setDescription("");
        setYoutubeUrl("");
        setProgress(0);
        setError(null);
        setSuccess(false);
    };

    const Icon = isTrack ? Music : Package;

    return (
        <div className="max-w-2xl mx-auto">
            <div className="p-8 rounded-2xl bg-zinc-900/60 backdrop-blur-sm border border-zinc-800/60">
                {/* Header */}
                <div className="flex items-center gap-4 mb-6">
                    <div className={`w-12 h-12 rounded-xl ${isTrack ? 'bg-violet-600/20 border-violet-500/30' : 'bg-amber-600/20 border-amber-500/30'} border flex items-center justify-center`}>
                        <Icon className={isTrack ? 'text-violet-400' : 'text-amber-400'} size={24} />
                    </div>
                    <div>
                        <h2 className="text-2xl font-bold text-white">
                            Upload {isTrack ? 'Track' : 'Album Pack'}
                        </h2>
                        <p className="text-sm text-zinc-500">
                            {isTrack ? 'Upload an audio file' : 'Upload a ZIP file containing your album'}
                        </p>
                    </div>
                </div>

                {/* Success Message */}
                {success && (
                    <div className="mb-6 p-4 rounded-xl bg-emerald-600/20 border border-emerald-500/40 flex items-center gap-3">
                        <Check className="text-emerald-400" size={20} />
                        <p className="text-emerald-400 font-semibold">
                            {isTrack ? 'Track' : 'Album'} uploaded successfully!
                        </p>
                    </div>
                )}

                {/* Error Message */}
                {error && (
                    <div className="mb-6 p-4 rounded-xl bg-red-600/20 border border-red-500/40 flex items-center gap-3">
                        <X className="text-red-400" size={20} />
                        <p className="text-red-400 font-semibold">{error}</p>
                    </div>
                )}

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* File Input */}
                    <div>
                        <label className="block text-sm font-bold text-white mb-2">
                            {isTrack ? 'Audio File' : 'ZIP File'} *
                        </label>
                        <input
                            type="file"
                            accept={acceptedTypes}
                            onChange={handleFileChange}
                            disabled={uploading}
                            className="w-full px-4 py-3 rounded-xl bg-zinc-800/60 border border-zinc-700/60 text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/60 transition-colors disabled:opacity-50"
                        />
                        {file && (
                            <p className="mt-2 text-sm text-zinc-500">
                                Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                            </p>
                        )}
                    </div>

                    {/* Cover Art Preview */}
                    {isTrack && coverPreview && (
                        <div className="flex items-center gap-4 p-4 bg-zinc-800/40 rounded-xl border border-zinc-700/40">
                            <div className="relative w-16 h-16 rounded overflow-hidden">
                                <img src={coverPreview} alt="Cover" className="w-full h-full object-cover" />
                            </div>
                            <div>
                                <p className="text-sm font-bold text-white">Cover Art Detected</p>
                                <p className="text-xs text-zinc-400">Extracted from file metadata</p>
                            </div>
                        </div>
                    )}

                    {/* Title */}
                    <div>
                        <label className="block text-sm font-bold text-white mb-2">
                            Title * {isAnalyzing && <span className="text-xs text-violet-400 animate-pulse ml-2">Reading tags...</span>}
                        </label>
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            disabled={uploading}
                            placeholder={isTrack ? "Enter track title" : "Enter album title"}
                            className="w-full px-4 py-3 rounded-xl bg-zinc-800/60 border border-zinc-700/60 text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/60 transition-colors disabled:opacity-50"
                        />
                    </div>

                    {/* Description (Albums only) */}
                    {!isTrack && (
                        <div>
                            <label className="block text-sm font-bold text-white mb-2">
                                Description
                            </label>
                            <textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                disabled={uploading}
                                placeholder="Describe your album pack"
                                rows={4}
                                className="w-full px-4 py-3 rounded-xl bg-zinc-800/60 border border-zinc-700/60 text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/60 transition-colors resize-none disabled:opacity-50"
                            />
                        </div>
                    )}

                    {/* YouTube URL (Tracks only) */}
                    {isTrack && (
                        <div className="space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-bold text-white mb-2">
                                        BPM {isAnalyzing && <span className="text-xs text-violet-400 animate-pulse">(Detecting...)</span>}
                                    </label>
                                    <input
                                        type="number"
                                        value={bpm}
                                        onChange={(e) => setBpm(Number(e.target.value) || "")}
                                        disabled={uploading}
                                        placeholder="128"
                                        className="w-full px-4 py-3 rounded-xl bg-zinc-800/60 border border-zinc-700/60 text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/60 transition-colors disabled:opacity-50"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-white mb-2">
                                        Genre {isAnalyzing && <span className="text-xs text-violet-400 animate-pulse">(Detecting...)</span>}
                                    </label>
                                    <input
                                        type="text"
                                        value={genre}
                                        onChange={(e) => setGenre(e.target.value)}
                                        disabled={uploading}
                                        placeholder="House, Techno..."
                                        className="w-full px-4 py-3 rounded-xl bg-zinc-800/60 border border-zinc-700/60 text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/60 transition-colors disabled:opacity-50"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-white mb-2">
                                    YouTube Preview URL
                                </label>
                                <input
                                    type="url"
                                    value={youtubeUrl}
                                    onChange={(e) => setYoutubeUrl(e.target.value)}
                                    disabled={uploading}
                                    placeholder="https://youtube.com/watch?v=..."
                                    className="w-full px-4 py-3 rounded-xl bg-zinc-800/60 border border-zinc-700/60 text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/60 transition-colors disabled:opacity-50"
                                />
                            </div>
                        </div>
                    )}

                    {/* Price */}
                    <div>
                        <label className="block text-sm font-bold text-white mb-2">
                            Price (INR) *
                        </label>
                        <div className="flex items-center gap-4">
                            <input
                                type="number"
                                value={price}
                                onChange={(e) => setPrice(Number(e.target.value))}
                                disabled={uploading || isFree}
                                min="0"
                                step="1"
                                placeholder="0"
                                className="flex-1 px-4 py-3 rounded-xl bg-zinc-800/60 border border-zinc-700/60 text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/60 transition-colors disabled:opacity-50"
                            />
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={isFree}
                                    onChange={(e) => {
                                        setIsFree(e.target.checked);
                                        if (e.target.checked) setPrice(0);
                                    }}
                                    disabled={uploading}
                                    className="w-5 h-5 rounded border-zinc-700 bg-zinc-800 text-violet-600 focus:ring-violet-500 focus:ring-offset-0"
                                />
                                <span className="text-sm font-semibold text-zinc-400">Free</span>
                            </label>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    {uploading && (
                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-semibold text-zinc-400">Uploading...</span>
                                <span className="text-sm font-bold text-violet-400">{progress}%</span>
                            </div>
                            <div className="w-full h-2 bg-zinc-800/60 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-gradient-to-r from-violet-600 to-violet-500 transition-all duration-300"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                        </div>
                    )}

                    {/* Submit Button */}
                    <div className="flex gap-4">
                        <Button
                            type="submit"
                            variant="primary"
                            size="lg"
                            loading={uploading}
                            disabled={!file || !title || (!isFree && price <= 0)}
                            className="flex-1"
                        >
                            <Upload size={20} />
                            Upload {isTrack ? 'Track' : 'Album'}
                        </Button>

                        {!uploading && (file || title || description || youtubeUrl) && (
                            <Button
                                type="button"
                                variant="outline"
                                size="lg"
                                onClick={resetForm}
                            >
                                Clear
                            </Button>
                        )}
                    </div>
                </form>
            </div>
        </div>
    );
}
