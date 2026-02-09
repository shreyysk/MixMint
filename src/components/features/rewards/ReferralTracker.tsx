"use client";

import { useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";

function TrackerContent() {
    const searchParams = useSearchParams();

    useEffect(() => {
        const ref = searchParams.get('ref');
        if (ref) {
            if (typeof window !== 'undefined') {
                localStorage.setItem('mixmint_ref', ref);
                console.log("[REFERRAL_TRACKED]:", ref);
            }
        }
    }, [searchParams]);

    return null;
}

/**
 * Component to capture referral code from URL and store in localStorage
 * Wrapped in Suspense because useSearchParams() requires it in static-rendered layouts
 */
export function ReferralTracker() {
    return (
        <Suspense fallback={null}>
            <TrackerContent />
        </Suspense>
    );
}
