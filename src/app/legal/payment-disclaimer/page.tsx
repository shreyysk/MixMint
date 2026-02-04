export default function PaymentDisclaimerPage() {
    return (
        <div className="min-h-screen pb-24">
            <div className="px-6 md:px-12 max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-12">
                    <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
                        Payment Information & Disclaimer
                    </h1>
                    <p className="text-zinc-500">
                        Last updated: February 4, 2026
                    </p>
                </div>

                {/* Content */}
                <div className="space-y-8 text-zinc-300 leading-relaxed">

                    {/* Payment Processor */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">1. Payment Processor</h2>
                        <p className="mb-4">
                            All payments on MixMint are processed securely through <strong className="text-white">Razorpay</strong>, a PCI DSS Level 1 compliant payment gateway authorized by the Reserve Bank of India (RBI).
                        </p>
                        <p className="mb-4">
                            MixMint does not store, process, or have access to your complete payment card information. All payment data is handled directly by Razorpay's secure infrastructure.
                        </p>
                        <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60">
                            <p className="text-sm text-zinc-400">
                                <strong className="text-white">Razorpay Payment Gateway:</strong> Razorpay Software Private Limited is a trusted payment service provider in India, ensuring secure and reliable transaction processing.
                            </p>
                        </div>
                    </section>

                    {/* Accepted Payment Methods */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">2. Accepted Payment Methods</h2>
                        <p className="mb-4">We accept the following payment methods through Razorpay:</p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>Credit Cards (Visa, Mastercard, American Express, RuPay)</li>
                            <li>Debit Cards (Visa, Mastercard, Maestro, RuPay)</li>
                            <li>Net Banking (all major Indian banks)</li>
                            <li>UPI (Google Pay, PhonePe, Paytm, BHIM, etc.)</li>
                            <li>Digital Wallets (Paytm, Mobikwik, etc.)</li>
                        </ul>
                        <p className="mt-4 text-sm text-zinc-500">
                            Availability of payment methods may vary based on your location and bank.
                        </p>
                    </section>

                    {/* Currency */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">3. Currency and Pricing</h2>
                        <p className="mb-4">
                            All prices on MixMint are displayed in <strong className="text-white">Indian Rupees (INR)</strong>.
                        </p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>Prices include all applicable taxes (GST, etc.)</li>
                            <li>DJs set their own pricing for tracks and albums</li>
                            <li>Subscription plans have fixed monthly pricing</li>
                            <li>Prices are subject to change at the DJ's or platform's discretion</li>
                        </ul>
                    </section>

                    {/* Transaction Process */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">4. Transaction Process</h2>

                        <h3 className="text-xl font-semibold text-white mb-3">4.1 Purchase Flow</h3>
                        <ol className="list-decimal list-inside space-y-3 text-zinc-400 mb-4">
                            <li>Select content or subscription plan</li>
                            <li>Review purchase details and pricing</li>
                            <li>Click "Purchase" or "Subscribe"</li>
                            <li>You will be redirected to Razorpay's secure payment page</li>
                            <li>Complete payment using your preferred method</li>
                            <li>Razorpay processes the transaction</li>
                            <li>Upon success, you are redirected back to MixMint</li>
                            <li>Content becomes immediately accessible</li>
                        </ol>

                        <h3 className="text-xl font-semibold text-white mb-3">4.2 Payment Confirmation</h3>
                        <p className="mb-4">
                            You will receive:
                        </p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>On-screen confirmation of successful payment</li>
                            <li>Email receipt from MixMint</li>
                            <li>Payment confirmation from Razorpay (optional)</li>
                            <li>Transaction ID for your records</li>
                        </ul>
                    </section>

                    {/* Payment Security */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">5. Payment Security</h2>
                        <p className="mb-4">
                            Your payment security is our priority:
                        </p>
                        <div className="space-y-4">
                            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60">
                                <h4 className="font-semibold text-white mb-2">🔒 SSL Encryption</h4>
                                <p className="text-sm text-zinc-400">
                                    All data transmitted between your browser and our servers is encrypted using industry-standard SSL/TLS protocols.
                                </p>
                            </div>

                            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60">
                                <h4 className="font-semibold text-white mb-2">🛡️ PCI DSS Compliance</h4>
                                <p className="text-sm text-zinc-400">
                                    Razorpay is PCI DSS Level 1 certified, the highest level of payment security certification.
                                </p>
                            </div>

                            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60">
                                <h4 className="font-semibold text-white mb-2">🔐 3D Secure</h4>
                                <p className="text-sm text-zinc-400">
                                    Card transactions use 3D Secure authentication (OTP verification) for additional security.
                                </p>
                            </div>

                            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60">
                                <h4 className="font-semibold text-white mb-2">✅ No Storage</h4>
                                <p className="text-sm text-zinc-400">
                                    We do not store your complete card details on our servers. Razorpay handles all sensitive payment data.
                                </p>
                            </div>
                        </div>
                    </section>

                    {/* Failed Payments */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">6. Failed or Declined Payments</h2>
                        <p className="mb-4">
                            If your payment fails or is declined:
                        </p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>You will be notified immediately on the payment page</li>
                            <li>No charges will be made to your account</li>
                            <li>You can retry the payment with the same or different method</li>
                            <li>Common reasons: insufficient funds, incorrect details, bank restrictions, network issues</li>
                        </ul>
                        <p className="mt-4">
                            If you continue to experience issues, please contact your bank or try an alternative payment method.
                        </p>
                    </section>

                    {/* Transaction Fees */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">7. Transaction Fees</h2>
                        <p className="mb-4">
                            <strong className="text-white">For Buyers:</strong> All displayed prices are final. There are no additional transaction fees charged to buyers.
                        </p>
                        <p>
                            <strong className="text-white">For DJs:</strong> Platform and payment processing fees are deducted from DJ earnings as per the DJ agreement.
                        </p>
                    </section>

                    {/* Subscription Billing */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">8. Subscription Billing</h2>
                        <p className="mb-4">
                            For subscription plans:
                        </p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>Billing occurs monthly on the same date you subscribed</li>
                            <li>Auto-renewal is enabled by default</li>
                            <li>You will receive a reminder email before each renewal</li>
                            <li>Cancel anytime to stop future charges (current period remains active)</li>
                            <li>Failed renewal payments may result in subscription suspension</li>
                        </ul>
                    </section>

                    {/* Taxes */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">9. Taxes and GST</h2>
                        <p className="mb-4">
                            All prices include applicable Goods and Services Tax (GST) as per Indian tax laws. GST-registered users will receive proper tax invoices.
                        </p>
                        <p>
                            Tax rates may change based on government regulations. Any changes will be reflected in the displayed prices.
                        </p>
                    </section>

                    {/* Disputes */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">10. Payment Disputes</h2>
                        <p className="mb-4">
                            If you notice an unauthorized or incorrect charge:
                        </p>
                        <ol className="list-decimal list-inside space-y-3 text-zinc-400">
                            <li>Contact us immediately at <strong className="text-white">support@mixmint.in</strong></li>
                            <li>Provide transaction ID and details of the issue</li>
                            <li>We will investigate and respond within 5-7 business days</li>
                            <li>If unresolved, you may raise a dispute with Razorpay or your bank</li>
                        </ol>
                        <p className="mt-4 text-amber-400">
                            <strong>Important:</strong> Initiating a chargeback without contacting us first may result in account suspension and loss of access to purchased content.
                        </p>
                    </section>

                    {/* Disclaimer */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">11. Disclaimer</h2>
                        <p className="mb-4">
                            While we strive to ensure smooth payment processing:
                        </p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>We are not responsible for payment gateway downtime or technical issues</li>
                            <li>Bank processing times are beyond our control</li>
                            <li>Currency conversion rates (if applicable) are determined by your bank</li>
                            <li>We reserve the right to modify accepted payment methods</li>
                        </ul>
                    </section>

                    {/* Contact */}
                    <section className="p-6 rounded-2xl bg-violet-600/10 border border-violet-500/20">
                        <h2 className="text-2xl font-bold text-white mb-4">12. Payment Support</h2>
                        <p className="mb-4">
                            For payment-related questions or issues:
                        </p>
                        <div className="space-y-2 text-zinc-300">
                            <p><strong>Email:</strong> payments@mixmint.in</p>
                            <p><strong>Support:</strong> support@mixmint.in</p>
                            <p><strong>Razorpay Support:</strong> Available through their website</p>
                        </div>
                    </section>

                </div>
            </div>
        </div>
    );
}
