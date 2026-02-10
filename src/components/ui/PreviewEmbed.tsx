"use client";

import React from "react";

interface PreviewEmbedProps {
    type: "youtube" | "instagram";
    embedId: string;
    className?: string;
}

export function PreviewEmbed({ type, embedId, className = "" }: PreviewEmbedProps) {
    if (type === "youtube") {
        return (
            <div className={`aspect-video w-full overflow-hidden rounded-xl bg-zinc-900 ${className}`}>
                <iframe
                    src={`https://www.youtube.com/embed/${embedId}?autoplay=0&controls=1&modestbranding=1&rel=0`}
                    title="YouTube video player"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                    className="w-full h-full border-0"
                ></iframe>
            </div>
        );
    }

    if (type === "instagram") {
        return (
            <div className={`w-full overflow-hidden rounded-xl bg-zinc-900 flex justify-center ${className}`}>
                <iframe
                    src={`https://www.instagram.com/reel/${embedId}/embed/`}
                    title="Instagram Reel player"
                    allowTransparency
                    allowFullScreen
                    className="w-full max-w-[400px] aspect-[9/16] border-0"
                ></iframe>
            </div>
        );
    }

    return null;
}
