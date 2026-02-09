"use client";

import { useState, useEffect } from "react";
import { SUBSCRIPTION_PLANS, SubscriptionPlan } from "@/lib/subscriptionPlans";
import { Button } from "@/components/ui/Button";
import { Loader2, Check, Sparkles, Crown, Star, Zap } from "lucide-react";
import { useAuth } from "@/lib/AuthContext";
import { subscribeToDJ } from "@/lib/razorpayCheckout";
import { supabase } from "@/lib/supabaseClient";
import { cn } from "@/lib/utils";

interface Props {
    djId: string;
    djName: string;
}

const PLAN_ICONS: Record<SubscriptionPlan, React.ReactNode> = {
    basic: <Star className="w-6 h-6" />,
    pro: <Zap className="w-6 h-6" />,
    super: <Crown className="w-6 h-6" />,
};

const PLAN_GRADIENTS: Record<SubscriptionPlan, string> = {
    basic: "from-zinc-700 to-zinc-800",
    pro: "from-purple-primary to-purple-700",
    super: "from-gold via-amber-500 to-orange-500",
};

export default function SubscriptionPlans({ djId, djName }: Props) {
    const { user } = useAuth();
    const [loading, setLoading] = useState<string | null>(null);
    const [userPoints, setUserPoints] = useState(0);
    const [redeemPoints, setRedeemPoints] = useState(false);

    useEffect(() => {
        if (user) {
            fetchPoints();
        }
    }, [user]);

    async function fetchPoints() {
        const { data } = await supabase.from('points').select('balance').eq('profile_id', user?.id).single();
        if (data) setUserPoints(data.balance);
    }

    const handleSubscribe = async (plan: SubscriptionPlan) => {
        if (!user) {
            alert("Please login to subscribe.");
            return;
        }

        setLoading(plan);
        try {
            await subscribeToDJ({
                djId,
                plan,
                userEmail: user.email || undefined,
                userName: user.user_metadata?.full_name || undefined,
                pointsToRedeem: redeemPoints ? Math.min(userPoints, Math.floor(SUBSCRIPTION_PLANS[plan].price_inr * 0.2)) : 0,
                onSuccess: () => {
                    console.log("Subscription successful");
                },
                onFailure: (error) => {
                    console.error("Subscription failed:", error);
                    alert(`Subscription failed: ${error}`);
                }
            });
        } catch (err: any) {
            alert(err.message);
        } finally {
            setLoading(null);
        }
    };

    return (
        <div className="flex flex-col gap-8 my-12">
            {/* Points Redemption Banner */}
            {userPoints > 0 && (
                <div className="max-w-md mx-auto w-full p-4 rounded-2xl glass border border-gold/30">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-gold/20 flex items-center justify-center">
                                <Sparkles size={18} className="text-gold" />
                            </div>
                            <div>
                                <p className="font-heading font-bold text-white">{userPoints} Points Available</p>
                                <p className="text-xs text-zinc-400">Redeem up to 20% discount</p>
                            </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                            <input
                                type="checkbox"
                                checked={redeemPoints}
                                onChange={() => setRedeemPoints(!redeemPoints)}
                                className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-zinc-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gold"></div>
                        </label>
                    </div>
                </div>
            )}

            {/* Plans Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {(Object.entries(SUBSCRIPTION_PLANS) as [SubscriptionPlan, typeof SUBSCRIPTION_PLANS.basic][]).map(([key, plan]) => {
                    const discount = redeemPoints ? Math.min(userPoints, Math.floor(plan.price_inr * 0.2)) : 0;
                    const finalPrice = plan.price_inr - discount;
                    const isPro = key === 'pro';
                    const isSuper = key === 'super';

                    return (
                        <div
                            key={key}
                            className={cn(
                                "relative rounded-2xl overflow-hidden transition-all duration-300 hover:-translate-y-1",
                                isPro && "ring-2 ring-purple-primary shadow-purple-glow",
                                isSuper && "ring-2 ring-gold shadow-[0_0_30px_rgba(245,158,11,0.3)]"
                            )}
                        >
                            {/* Popular badge */}
                            {isPro && (
                                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-purple-primary text-white text-[10px] font-bold px-3 py-1 rounded-full z-10">
                                    POPULAR
                                </div>
                            )}

                            {/* Card */}
                            <div className={cn(
                                "h-full flex flex-col p-6 bg-surface-dark border border-white/5",
                                isPro && "border-purple-primary/30",
                                isSuper && "border-gold/30"
                            )}>
                                {/* Header */}
                                <div className={cn(
                                    "inline-flex items-center gap-2 px-3 py-1.5 rounded-full w-fit mb-4 bg-gradient-to-r",
                                    PLAN_GRADIENTS[key as SubscriptionPlan]
                                )}>
                                    {PLAN_ICONS[key as SubscriptionPlan]}
                                    <span className="font-heading font-bold text-white capitalize">{key}</span>
                                </div>

                                {/* Price */}
                                <div className="mb-6">
                                    <div className="flex items-baseline gap-2">
                                        <span className={cn(
                                            "text-4xl font-heading font-bold",
                                            isPro && "text-purple-primary-dark",
                                            isSuper && "text-gold",
                                            !isPro && !isSuper && "text-white"
                                        )}>
                                            ₹{finalPrice}
                                        </span>
                                        {discount > 0 && (
                                            <span className="text-sm text-zinc-500 line-through">₹{plan.price_inr}</span>
                                        )}
                                    </div>
                                    <span className="text-xs text-zinc-500">per month</span>
                                </div>

                                {/* Features */}
                                <ul className="space-y-3 mb-8 flex-1">
                                    <li className="flex items-center gap-3 text-sm text-zinc-300">
                                        <Check className={cn(
                                            "w-4 h-4 flex-shrink-0",
                                            isPro && "text-purple-primary",
                                            isSuper && "text-gold",
                                            !isPro && !isSuper && "text-mint-accent"
                                        )} />
                                        <span>{plan.track_quota} Track Downloads</span>
                                    </li>
                                    <li className="flex items-center gap-3 text-sm text-zinc-300">
                                        <Check className={cn(
                                            "w-4 h-4 flex-shrink-0",
                                            isPro && "text-purple-primary",
                                            isSuper && "text-gold",
                                            !isPro && !isSuper && "text-mint-accent"
                                        )} />
                                        <span>{plan.zip_quota} Album Packs</span>
                                    </li>
                                    {plan.fan_upload_quota > 0 && (
                                        <li className="flex items-center gap-3 text-sm text-zinc-300">
                                            <Check className={cn(
                                                "w-4 h-4 flex-shrink-0",
                                                isSuper ? "text-gold" : "text-purple-primary"
                                            )} />
                                            <span>{plan.fan_upload_quota} Fan Exclusives</span>
                                        </li>
                                    )}
                                    <li className="flex items-center gap-3 text-sm text-zinc-500">
                                        <Check className="w-4 h-4 flex-shrink-0" />
                                        <span>IP-Locked Downloads</span>
                                    </li>
                                </ul>

                                {/* CTA */}
                                <Button
                                    onClick={() => handleSubscribe(key as SubscriptionPlan)}
                                    disabled={loading === key}
                                    className={cn(
                                        "w-full font-bold",
                                        isPro && "btn-primary",
                                        isSuper && "bg-gradient-super text-white hover:opacity-90",
                                        !isPro && !isSuper && "bg-zinc-800 text-white hover:bg-zinc-700"
                                    )}
                                >
                                    {loading === key ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        `Subscribe to ${key.charAt(0).toUpperCase() + key.slice(1)}`
                                    )}
                                </Button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
