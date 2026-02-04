import React, { useState } from "react";
import { Copy, Check, Share2, Users } from "lucide-react";
import { Button } from "@/app/components/ui/Button";
import { motion, AnimatePresence } from "framer-motion";

interface ReferralLinkProps {
    code: string;
    link: string;
    stats: {
        totalInvites: number;
        successfulReferrals: number;
    };
    description?: React.ReactNode;
}

export function ReferralLink({ code, link, stats, description }: ReferralLinkProps) {
    const [copied, setCopied] = useState(false);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(link);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="space-y-6">
            {/* Referral Stats Summary */}
            <div className="grid grid-cols-2 gap-4">
                <div className="p-6 rounded-2xl bg-zinc-900/60 border border-zinc-800">
                    <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-1">Total Invites</p>
                    <p className="text-2xl font-black text-white italic tracking-tighter">{stats.totalInvites}</p>
                </div>
                <div className="p-6 rounded-2xl bg-zinc-900/60 border border-zinc-800">
                    <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-1">Conversions</p>
                    <p className="text-2xl font-black text-violet-400 italic tracking-tighter">{stats.successfulReferrals}</p>
                </div>
            </div>

            {/* Referral Link Card */}
            <div className="p-8 rounded-[2rem] bg-zinc-900/40 border border-zinc-800 backdrop-blur-xl">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center">
                        <Share2 className="text-violet-400" size={20} />
                    </div>
                    <h3 className="text-lg font-black text-white uppercase italic tracking-tight">Invite your Tribe</h3>
                </div>

                <div className="text-sm text-zinc-500 font-bold mb-6 leading-relaxed italic">
                    {description || (
                        <>
                            Share your link and earn <span className="text-amber-500">20 Pts</span> for every signup,
                            plus <span className="text-amber-500">100 Pts</span> when they make their first purchase.
                        </>
                    )}
                </div>

                <div className="relative group">
                    <div
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-2xl px-5 py-4 text-sm font-medium text-zinc-300 pr-24 overflow-hidden text-ellipsis whitespace-nowrap cursor-pointer hover:bg-zinc-900 transition-colors"
                        onClick={copyToClipboard}
                    >
                        {link}
                    </div>
                    <div className="absolute inset-y-0 right-2 flex items-center">
                        <Button
                            variant="secondary"
                            size="sm"
                            onClick={(e) => {
                                e.stopPropagation();
                                copyToClipboard();
                            }}
                            className="rounded-xl h-10 px-4 group-hover:bg-zinc-800 transition-colors"
                        >
                            <AnimatePresence mode="wait" initial={false}>
                                {copied ? (
                                    <motion.div
                                        key="check"
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        exit={{ scale: 0 }}
                                        className="flex items-center gap-2 text-emerald-400"
                                    >
                                        <Check size={14} />
                                        <span className="text-[10px] font-black uppercase tracking-widest">Copied</span>
                                    </motion.div>
                                ) : (
                                    <motion.div
                                        key="copy"
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        exit={{ scale: 0 }}
                                        className="flex items-center gap-2"
                                    >
                                        <Copy size={14} />
                                        <span className="text-[10px] font-black uppercase tracking-widest">Copy</span>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </Button>
                    </div>
                </div>

                <div className="mt-8 flex items-center gap-4 p-4 rounded-xl bg-violet-600/5 border border-violet-500/10">
                    <div className="w-10 h-10 rounded-lg bg-violet-600/20 flex items-center justify-center shrink-0">
                        <Users className="text-violet-400" size={18} />
                    </div>
                    <p className="text-[10px] text-zinc-500 font-bold leading-tight uppercase tracking-widest">
                        Referral Code: <span className="text-white font-black ml-1">{code}</span>
                    </p>
                </div>
            </div>
        </div>
    );
}
