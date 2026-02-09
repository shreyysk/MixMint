import React from "react";
import { History, TrendingUp, ShoppingCart, UserPlus, Gift } from "lucide-react";
import { motion } from "framer-motion";

interface PointsEvent {
    id: string;
    amount: number;
    type: string;
    description: string;
    created_at: string;
}

interface PointsHistoryProps {
    history: PointsEvent[];
}

export function PointsHistory({ history }: PointsHistoryProps) {
    const getEventIcon = (type: string) => {
        switch (type) {
            case 'signup_bonus': return <Gift className="text-emerald-400" size={16} />;
            case 'purchase': return <ShoppingCart className="text-violet-400" size={16} />;
            case 'referral_signup': return <UserPlus className="text-blue-400" size={16} />;
            case 'referral_conversion': return <TrendingUp className="text-amber-400" size={16} />;
            default: return <Gift className="text-zinc-400" size={16} />;
        }
    };

    const getEventLabel = (type: string) => {
        switch (type) {
            case 'signup_bonus': return 'Welcome Bonus';
            case 'purchase': return 'Content Purchase';
            case 'referral_signup': return 'New Referral';
            case 'referral_conversion': return 'Referral Purchase';
            default: return type.replace('_', ' ');
        }
    };

    return (
        <div className="bg-zinc-900/40 border border-zinc-800 rounded-[2rem] backdrop-blur-xl overflow-hidden">
            <div className="px-8 py-6 border-b border-zinc-800 flex items-center gap-3">
                <History className="text-zinc-600" size={20} />
                <h3 className="text-lg font-black text-white uppercase italic tracking-tight">Recent Activity</h3>
            </div>

            <div className="divide-y divide-zinc-800/50">
                {history.length === 0 ? (
                    <div className="px-8 py-12 text-center">
                        <p className="text-zinc-500 font-bold italic">No points Activity yet. Start earning!</p>
                    </div>
                ) : (
                    history.map((event, idx) => (
                        <motion.div
                            key={event.id}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.05 }}
                            className="px-8 py-5 flex items-center justify-between hover:bg-zinc-800/30 transition-colors"
                        >
                            <div className="flex items-center gap-4">
                                <div className="w-10 h-10 rounded-xl bg-zinc-800/80 border border-zinc-700/50 flex items-center justify-center">
                                    {getEventIcon(event.type)}
                                </div>
                                <div>
                                    <p className="text-sm font-black text-white uppercase italic tracking-tight">
                                        {getEventLabel(event.type)}
                                    </p>
                                    <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mt-0.5">
                                        {new Date(event.created_at).toLocaleDateString(undefined, {
                                            month: 'short',
                                            day: 'numeric',
                                            year: 'numeric'
                                        })}
                                    </p>
                                </div>
                            </div>
                            <div className={`text-lg font-black italic tracking-tighter ${event.amount > 0 ? 'text-amber-400' : 'text-zinc-500'}`}>
                                {event.amount > 0 ? '+' : ''}{event.amount}
                            </div>
                        </motion.div>
                    ))
                )}
            </div>
        </div>
    );
}
