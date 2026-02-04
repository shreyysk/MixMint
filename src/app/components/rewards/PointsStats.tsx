import React from "react";
import { Trophy, Star, History } from "lucide-react";
import { motion } from "framer-motion";

interface PointsStatsProps {
    balance: number;
    totalEarned: number;
}

export function PointsStats({ balance, totalEarned }: PointsStatsProps) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-8 rounded-[2rem] bg-gradient-to-br from-amber-500/20 to-amber-600/5 border border-amber-500/30 backdrop-blur-xl relative overflow-hidden group"
            >
                <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/10 blur-3xl rounded-full -mr-16 -mt-16 group-hover:bg-amber-500/20 transition-colors" />

                <div className="flex items-center gap-4 mb-4">
                    <div className="w-14 h-14 rounded-2xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center shadow-lg shadow-amber-500/10">
                        <Trophy className="text-amber-400" size={28} />
                    </div>
                    <div>
                        <p className="text-xs font-black text-amber-500/80 uppercase tracking-[0.2em]">Current Balance</p>
                        <h2 className="text-4xl font-black text-white italic tracking-tighter">
                            {balance.toLocaleString()} <span className="text-lg not-italic text-amber-500/60 uppercase ml-1">Pts</span>
                        </h2>
                    </div>
                </div>
                <p className="text-sm text-zinc-500 font-bold italic">
                    Use these for exclusive drops and future rewards.
                </p>
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="p-8 rounded-[2rem] bg-zinc-900/40 border border-zinc-800 backdrop-blur-xl group hover:border-zinc-700 transition-colors"
            >
                <div className="flex items-center gap-4 mb-4">
                    <div className="w-14 h-14 rounded-2xl bg-zinc-800 border border-zinc-700 flex items-center justify-center">
                        <Star className="text-zinc-400 group-hover:text-amber-400 transition-colors" size={28} />
                    </div>
                    <div>
                        <p className="text-xs font-black text-zinc-500 uppercase tracking-[0.2em]">Total Earned</p>
                        <h2 className="text-3xl font-black text-white italic tracking-tighter">
                            {totalEarned.toLocaleString()} <span className="text-base not-italic text-zinc-600 uppercase ml-1">Pts</span>
                        </h2>
                    </div>
                </div>
                <p className="text-sm text-zinc-500 font-bold italic">
                    Lifetime achievement rewards coming soon!
                </p>
            </motion.div>
        </div>
    );
}
