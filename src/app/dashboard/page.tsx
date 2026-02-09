
"use client";

import { DJDashboard } from "@/app/components/dashboard/DJDashboard";
import { useAuth } from "@/app/lib/AuthContext";
import Link from "next/link";
import { Button } from "@/app/components/ui/Button";

export default function DashboardPage() {
    const { user } = useAuth();

    if (!user) {
        return (
            <div className="min-h-screen flex items-center justify-center text-center">
                <div>
                    <h1 className="text-2xl font-bold mb-4">Please log in</h1>
                    <p className="text-zinc-500 mb-8">You need to be logged in to view your dashboard.</p>
                    <Link href="/auth/login">
                        <Button>Log In</Button>
                    </Link>
                </div>
            </div>
        )
    }

    if (user.role !== 'dj') {
        return (
            <div className="min-h-screen flex items-center justify-center text-center">
                 <div>
                    <h1 className="text-2xl font-bold mb-4">Not a DJ</h1>
                    <p className="text-zinc-500 mb-8">Only DJs can access the dashboard.</p>
                    <Link href="/dj/apply">
                        <Button>Apply to be a DJ</Button>
                    </Link>
                </div>
            </div>
        )
    }

    return <DJDashboard />;
}
