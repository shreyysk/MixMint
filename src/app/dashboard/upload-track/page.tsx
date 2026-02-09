
"use client";

import { UploadTrackForm } from "@/components/features/dashboard/UploadTrackForm";

export default function UploadTrackPage() {
    return (
        <div className="min-h-screen pb-24">
            <div className="px-6 md:px-12">
                <div className="max-w-4xl mx-auto">
                    <h1 className="text-4xl md:text-5xl font-bold text-white mb-10">Upload New Track</h1>
                    <UploadTrackForm />
                </div>
            </div>
        </div>
    );
}
