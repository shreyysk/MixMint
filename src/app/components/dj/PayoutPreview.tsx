import React from "react";
import { Wallet, Clock, Info } from "lucide-react";

interface PayoutPreviewProps {
    availableBalance: number;
    pendingBalance: number;
}

export function PayoutPreview({
    availableBalance,
    pendingBalance,
}: PayoutPreviewProps) {
    const formatCurrency = (amount: number) => {
        return `₹${amount.toLocaleString('en-IN')}`;
    };

    return (
        <div className="space-y-6">
            {/* Info Banner */}
            <div className="p-6 rounded-2xl bg-amber-600/10 border border-amber-500/30 backdrop-blur-sm">
                <div className="flex items-start gap-3">
                    <Info className="text-amber-400 shrink-0 mt-0.5" size={20} />
                    <div>
                        <h3 className="text-lg font-bold text-amber-400 mb-2">
                            Payouts Coming Soon
                        </h3>
                        <p className="text-sm text-zinc-400 leading-relaxed">
                            We're working on enabling direct payouts to your bank account. In the meantime,
                            you can track your earnings here. Payout functionality will be available soon!
                        </p>
                    </div>
                </div>
            </div>

            {/* Balance Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {/* Available Balance */}
                <div className="p-8 rounded-2xl bg-gradient-to-br from-emerald-600/20 to-emerald-600/5 border border-emerald-500/40 backdrop-blur-sm">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-12 h-12 rounded-xl bg-emerald-600/30 border border-emerald-500/50 flex items-center justify-center">
                            <Wallet className="text-emerald-400" size={24} />
                        </div>
                        <div>
                            <p className="text-sm font-semibold text-emerald-400 uppercase tracking-wide">
                                Available Balance
                            </p>
                            <h2 className="text-3xl md:text-4xl font-extrabold text-white">
                                {formatCurrency(availableBalance)}
                            </h2>
                        </div>
                    </div>
                    <p className="text-xs text-zinc-500">
                        Ready for withdrawal (when payouts are enabled)
                    </p>
                </div>

                {/* Pending Balance */}
                <div className="p-8 rounded-2xl bg-gradient-to-br from-violet-600/20 to-violet-600/5 border border-violet-500/40 backdrop-blur-sm">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-12 h-12 rounded-xl bg-violet-600/30 border border-violet-500/50 flex items-center justify-center">
                            <Clock className="text-violet-400" size={24} />
                        </div>
                        <div>
                            <p className="text-sm font-semibold text-violet-400 uppercase tracking-wide">
                                Pending Balance
                            </p>
                            <h2 className="text-3xl md:text-4xl font-extrabold text-white">
                                {formatCurrency(pendingBalance)}
                            </h2>
                        </div>
                    </div>
                    <p className="text-xs text-zinc-500">
                        Processing (will be available soon)
                    </p>
                </div>
            </div>

            {/* Additional Info */}
            <div className="p-6 rounded-2xl bg-zinc-900/60 border border-zinc-800/60 backdrop-blur-sm">
                <h3 className="text-lg font-bold text-white mb-4">Payout Information</h3>
                <div className="space-y-3 text-sm text-zinc-400">
                    <div className="flex items-start gap-3">
                        <div className="w-1.5 h-1.5 rounded-full bg-violet-400 mt-2 shrink-0" />
                        <p>
                            <strong className="text-white">Minimum Payout:</strong> ₹500 (when enabled)
                        </p>
                    </div>
                    <div className="flex items-start gap-3">
                        <div className="w-1.5 h-1.5 rounded-full bg-violet-400 mt-2 shrink-0" />
                        <p>
                            <strong className="text-white">Processing Time:</strong> 3-5 business days
                        </p>
                    </div>
                    <div className="flex items-start gap-3">
                        <div className="w-1.5 h-1.5 rounded-full bg-violet-400 mt-2 shrink-0" />
                        <p>
                            <strong className="text-white">Payment Method:</strong> Direct bank transfer (UPI/NEFT)
                        </p>
                    </div>
                    <div className="flex items-start gap-3">
                        <div className="w-1.5 h-1.5 rounded-full bg-violet-400 mt-2 shrink-0" />
                        <p>
                            <strong className="text-white">Platform Fee:</strong> Deducted as per DJ agreement
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
