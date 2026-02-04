export default function RefundPolicyPage() {
    return (
        <div className="min-h-screen pb-24">
            <div className="px-6 md:px-12 max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-12">
                    <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
                        Refund & Cancellation Policy
                    </h1>
                    <p className="text-zinc-500">
                        Last updated: February 4, 2026
                    </p>
                </div>

                {/* Important Notice */}
                <div className="mb-8 p-6 rounded-2xl bg-amber-600/10 border border-amber-500/20">
                    <h3 className="text-lg font-bold text-amber-400 mb-3">Important Notice</h3>
                    <p className="text-zinc-300">
                        MixMint sells digital goods (audio files and subscriptions). Due to the nature of digital products, all sales are generally final and non-refundable. However, we review refund requests on a case-by-case basis for exceptional circumstances.
                    </p>
                </div>

                {/* Content */}
                <div className="space-y-8 text-zinc-300 leading-relaxed">

                    {/* Digital Goods Policy */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">1. Digital Goods Policy</h2>
                        <p className="mb-4">
                            All content sold on MixMint (tracks, albums, and subscription access) is delivered digitally and immediately accessible upon purchase. Once you have downloaded or accessed the content, the transaction is considered complete.
                        </p>
                        <p className="mb-4">
                            <strong>By making a purchase, you acknowledge and agree that:</strong>
                        </p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>Digital goods are non-refundable by default</li>
                            <li>You waive any right to a "cooling-off" period</li>
                            <li>Refunds are not guaranteed and are granted at our sole discretion</li>
                            <li>Subscription renewals are non-refundable once processed</li>
                        </ul>
                    </section>

                    {/* Exceptional Circumstances */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">2. Exceptional Circumstances</h2>
                        <p className="mb-4">
                            We may consider refund requests in the following exceptional cases:
                        </p>

                        <div className="space-y-4">
                            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60">
                                <h4 className="font-semibold text-white mb-2">Technical Issues</h4>
                                <p className="text-sm text-zinc-400">
                                    If you are unable to download or access purchased content due to a technical error on our platform, and we cannot resolve the issue within a reasonable timeframe.
                                </p>
                            </div>

                            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60">
                                <h4 className="font-semibold text-white mb-2">Duplicate Charges</h4>
                                <p className="text-sm text-zinc-400">
                                    If you were charged multiple times for the same transaction due to a payment processing error.
                                </p>
                            </div>

                            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60">
                                <h4 className="font-semibold text-white mb-2">Unauthorized Transactions</h4>
                                <p className="text-sm text-zinc-400">
                                    If you can demonstrate that a purchase was made without your authorization. You must report this within 48 hours of the transaction.
                                </p>
                            </div>

                            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60">
                                <h4 className="font-semibold text-white mb-2">Significantly Defective Content</h4>
                                <p className="text-sm text-zinc-400">
                                    If the downloaded content is corrupted, incomplete, or significantly different from what was advertised, and the issue cannot be resolved.
                                </p>
                            </div>
                        </div>
                    </section>

                    {/* Non-Refundable Situations */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">3. Non-Refundable Situations</h2>
                        <p className="mb-4">
                            Refunds will <strong>NOT</strong> be granted in the following cases:
                        </p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>Change of mind or buyer's remorse</li>
                            <li>Dissatisfaction with content quality or style (subjective preferences)</li>
                            <li>Accidental purchases (please review before confirming payment)</li>
                            <li>Inability to use content due to user's equipment or software</li>
                            <li>Subscription cancellations after the billing cycle has started</li>
                            <li>Content already downloaded or accessed</li>
                            <li>Violation of our Terms of Service</li>
                        </ul>
                    </section>

                    {/* Subscription Cancellations */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">4. Subscription Cancellations</h2>

                        <h3 className="text-xl font-semibold text-white mb-3">4.1 How to Cancel</h3>
                        <p className="mb-4">
                            You may cancel your subscription at any time from your account dashboard. Cancellation will take effect at the end of your current billing period.
                        </p>

                        <h3 className="text-xl font-semibold text-white mb-3">4.2 Cancellation Policy</h3>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400 mb-4">
                            <li>Cancellations must be made before the next billing date</li>
                            <li>No refunds for partial months or unused subscription time</li>
                            <li>Access continues until the end of the paid period</li>
                            <li>Previously downloaded content may remain accessible</li>
                        </ul>

                        <h3 className="text-xl font-semibold text-white mb-3">4.3 Auto-Renewal</h3>
                        <p>
                            Subscriptions automatically renew unless cancelled. You are responsible for cancelling before the renewal date if you do not wish to continue. Renewal charges are non-refundable.
                        </p>
                    </section>

                    {/* Refund Request Process */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">5. How to Request a Refund</h2>
                        <p className="mb-4">
                            If you believe you qualify for a refund under exceptional circumstances:
                        </p>
                        <ol className="list-decimal list-inside space-y-3 text-zinc-400">
                            <li>Contact us at <strong className="text-white">support@mixmint.in</strong> within <strong className="text-white">7 days</strong> of the transaction</li>
                            <li>Include your transaction ID, purchase details, and reason for the refund request</li>
                            <li>Provide any supporting evidence (screenshots, error messages, etc.)</li>
                            <li>Wait for our team to review your request (typically 5-7 business days)</li>
                        </ol>
                    </section>

                    {/* Razorpay Disputes */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">6. Payment Disputes via Razorpay</h2>
                        <p className="mb-4">
                            All payments are processed through Razorpay. If you have a payment-related dispute:
                        </p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>Contact us first at support@mixmint.in</li>
                            <li>If unresolved, you may raise a dispute with Razorpay</li>
                            <li>Razorpay's dispute resolution process will apply</li>
                            <li>We will cooperate with Razorpay's investigation</li>
                        </ul>
                        <p className="mt-4">
                            Note: Raising a chargeback or dispute without contacting us first may result in account suspension.
                        </p>
                    </section>

                    {/* Refund Processing */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">7. Refund Processing</h2>
                        <p className="mb-4">
                            If a refund is approved:
                        </p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>Refunds will be processed to the original payment method</li>
                            <li>Processing time: 5-10 business days from approval</li>
                            <li>Bank processing may take additional 3-7 business days</li>
                            <li>You will receive an email confirmation once processed</li>
                            <li>Access to the refunded content will be revoked</li>
                        </ul>
                    </section>

                    {/* DJ Payouts */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">8. DJ Payouts and Refunds</h2>
                        <p className="mb-4">
                            If a refund is issued for content purchased from a DJ:
                        </p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>The DJ's payout for that transaction will be reversed</li>
                            <li>DJs will be notified of refund requests</li>
                            <li>Platform fees are non-refundable to DJs</li>
                        </ul>
                    </section>

                    {/* Consumer Rights */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">9. Consumer Rights (India)</h2>
                        <p className="mb-4">
                            This policy complies with the Consumer Protection Act, 2019. Nothing in this policy limits your statutory rights as a consumer under Indian law.
                        </p>
                        <p>
                            If you believe your consumer rights have been violated, you may file a complaint with the appropriate consumer forum.
                        </p>
                    </section>

                    {/* Contact */}
                    <section className="p-6 rounded-2xl bg-violet-600/10 border border-violet-500/20">
                        <h2 className="text-2xl font-bold text-white mb-4">10. Contact Us</h2>
                        <p className="mb-4">
                            For refund requests or questions about this policy:
                        </p>
                        <div className="space-y-2 text-zinc-300">
                            <p><strong>Email:</strong> support@mixmint.in</p>
                            <p><strong>Subject Line:</strong> "Refund Request - [Transaction ID]"</p>
                            <p><strong>Response Time:</strong> 5-7 business days</p>
                        </div>
                    </section>

                </div>
            </div>
        </div>
    );
}
