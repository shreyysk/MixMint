"use client";

import React from "react";
import { X } from "lucide-react";
import { PreviewEmbed } from "./PreviewEmbed";

interface PreviewModalProps {
    isOpen: boolean;
    onClose: () => void;
    trackTitle: string;
    previews: Array<{
        type: "youtube" | "instagram";
        embedId: string;
        isPrimary: boolean;
    }>;
}

export function PreviewModal({ isOpen, onClose, trackTitle, previews }: PreviewModalProps) {
    const [activeTab, setActiveTab] = React.useState<number>(0);

    if (!isOpen) return null;

    const activePreview = previews[activeTab] || previews[0];

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal Content */}
            <div className="relative w-full max-w-4xl bg-zinc-950 border border-zinc-800 rounded-3xl overflow-hidden shadow-[0_0_50px_rgba(0,0,0,0.5)] animate-in fade-in zoom-in duration-300">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-zinc-800">
                    <div>
                        <h2 className="text-xl font-heading font-bold text-white uppercase italic tracking-tight">{trackTitle}</h2>
                        <p className="text-sm text-zinc-500 font-bold uppercase tracking-widest mt-1">Preview Mode</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-xl bg-zinc-900 text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6">
                    {previews.length > 1 && (
                        <div className="flex gap-2 mb-6">
                            {previews.map((preview, index) => (
                                <button
                                    key={index}
                                    onClick={() => setActiveTab(index)}
                                    className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${activeTab === index
                                            ? "bg-purple-primary text-white shadow-purple-glow"
                                            : "bg-zinc-900 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                                        }`}
                                >
                                    {preview.type}
                                </button>
                            ))}
                        </div>
                    )}

                    <div className="flex flex-col items-center">
                        {activePreview ? (
                            <PreviewEmbed
                                type={activePreview.type}
                                embedId={activePreview.embedId}
                                className="w-full"
                            />
                        ) : (
                            <div className="aspect-video w-full flex flex-col items-center justify-center bg-zinc-900 rounded-xl border border-dashed border-zinc-800 text-zinc-500">
                                <p className="font-bold uppercase tracking-widest">No preview available</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-zinc-800 bg-zinc-900/30 flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-6 py-3 rounded-xl bg-zinc-800 text-white text-sm font-black uppercase tracking-widest hover:bg-zinc-700 transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
