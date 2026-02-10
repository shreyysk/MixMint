'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar } from '@/components/ui/Avatar';
import { Music, UserPlus, MessageSquare, Trophy, Clock } from 'lucide-react';
import Link from 'next/link';

interface Activity {
    id: string;
    user_id: string;
    action_type: 'release' | 'follow' | 'comment' | 'milestone';
    entity_id: string;
    entity_type: 'track' | 'album' | 'dj' | 'comment';
    metadata: any;
    created_at: string;
    profiles: {
        full_name: string;
        avatar_url: string;
    };
}

export function ActivityFeed() {
    const [activities, setActivities] = useState<Activity[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadActivities();
    }, []);

    async function loadActivities() {
        try {
            const { data, error } = await supabase
                .from('activity_feed')
                .select(`
                    *,
                    profiles (full_name, avatar_url)
                `)
                .order('created_at', { ascending: false })
                .limit(20);

            if (error) throw error;
            setActivities(data || []);
        } catch (err) {
            console.error('[ACTIVITY_FEED_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    const getIcon = (type: string) => {
        switch (type) {
            case 'release': return <Music className="w-4 h-4 text-purple-400" />;
            case 'follow': return <UserPlus className="w-4 h-4 text-blue-400" />;
            case 'comment': return <MessageSquare className="w-4 h-4 text-pink-400" />;
            case 'milestone': return <Trophy className="w-4 h-4 text-yellow-400" />;
            default: return <Clock className="w-4 h-4 text-zinc-400" />;
        }
    };

    const formatActivity = (activity: Activity) => {
        const actorName = activity.profiles?.full_name || 'Someone';

        switch (activity.action_type) {
            case 'release':
                return (
                    <p className="text-sm text-zinc-300">
                        <span className="font-bold text-white">{actorName}</span> released a new {activity.entity_type}:
                        <span className="text-purple-400 ml-1 font-medium">{activity.metadata.title}</span>
                    </p>
                );
            case 'follow':
                return (
                    <p className="text-sm text-zinc-300">
                        <span className="font-bold text-white">{actorName}</span> started following
                        <span className="text-blue-400 ml-1 font-medium">{activity.metadata.targetName}</span>
                    </p>
                );
            case 'comment':
                return (
                    <p className="text-sm text-zinc-300">
                        <span className="font-bold text-white">{actorName}</span> commented on
                        <span className="text-pink-400 ml-1 font-medium">{activity.metadata.title}</span>
                    </p>
                );
            case 'milestone':
                return (
                    <p className="text-sm text-zinc-300">
                        <span className="font-bold text-white">{actorName}</span> reached a milestone:
                        <span className="text-yellow-400 ml-1 font-medium">{activity.metadata.description}</span>
                    </p>
                );
            default:
                return <p className="text-sm text-zinc-300">New activity from {actorName}</p>;
        }
    };

    return (
        <Card className="bg-zinc-950/50 border-zinc-800 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg font-heading font-bold text-white flex items-center gap-2">
                    <Clock className="w-5 h-5 text-purple-400" />
                    Activity Feed
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="space-y-6">
                    {loading ? (
                        Array.from({ length: 5 }).map((_, i) => (
                            <div key={i} className="flex gap-4 animate-pulse">
                                <div className="w-10 h-10 bg-zinc-800 rounded-full" />
                                <div className="flex-1 space-y-2">
                                    <div className="h-4 bg-zinc-800 rounded w-3/4" />
                                    <div className="h-3 bg-zinc-800 rounded w-1/4" />
                                </div>
                            </div>
                        ))
                    ) : activities.length > 0 ? (
                        activities.map((activity) => (
                            <div key={activity.id} className="flex gap-4 group">
                                <div className="relative">
                                    <Avatar
                                        src={activity.profiles?.avatar_url}
                                        fallback={activity.profiles?.full_name?.[0] || '?'}
                                        className="w-10 h-10 border border-zinc-800 group-hover:border-purple-500/50 transition-colors"
                                    />
                                    <div className="absolute -bottom-1 -right-1 bg-zinc-900 border border-zinc-800 rounded-full p-1 shadow-lg">
                                        {getIcon(activity.action_type)}
                                    </div>
                                </div>
                                <div className="flex-1 min-w-0">
                                    {formatActivity(activity)}
                                    <p className="text-[10px] text-zinc-500 mt-1 uppercase tracking-widest font-bold">
                                        {new Date(activity.created_at).toLocaleDateString()}
                                    </p>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="text-center py-8">
                            <p className="text-zinc-500 text-sm">No recent activity found.</p>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
