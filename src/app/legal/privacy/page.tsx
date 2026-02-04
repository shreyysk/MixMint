export default function PrivacyPolicyPage() {
    return (
        <div className="min-h-screen pb-24">
            <div className="px-6 md:px-12 max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-12">
                    <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
                        Privacy Policy
                    </h1>
                    <p className="text-zinc-500">
                        Last updated: February 4, 2026
                    </p>
                </div>

                {/* Content */}
                <div className="space-y-8 text-zinc-300 leading-relaxed">

                    {/* Introduction */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">1. Introduction</h2>
                        <p className="mb-4">
                            Welcome to MixMint ("we," "our," or "us"). We are committed to protecting your personal information and your right to privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our platform.
                        </p>
                        <p>
                            This policy applies to all users in India and complies with the Information Technology Act, 2000 and the Information Technology (Reasonable Security Practices and Procedures and Sensitive Personal Data or Information) Rules, 2011.
                        </p>
                    </section>

                    {/* Information We Collect */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">2. Information We Collect</h2>

                        <h3 className="text-xl font-semibold text-white mb-3">2.1 Personal Information</h3>
                        <p className="mb-4">When you register or use our services, we may collect:</p>
                        <ul className="list-disc list-inside space-y-2 mb-4 text-zinc-400">
                            <li>Name and email address</li>
                            <li>Payment information (processed securely by Razorpay)</li>
                            <li>Profile information (for DJ accounts)</li>
                            <li>Content you upload (tracks, albums, metadata)</li>
                        </ul>

                        <h3 className="text-xl font-semibold text-white mb-3">2.2 Automatically Collected Information</h3>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>IP address and device information</li>
                            <li>Browser type and version</li>
                            <li>Usage data and analytics</li>
                            <li>Cookies and similar tracking technologies</li>
                        </ul>
                    </section>

                    {/* How We Use Your Information */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">3. How We Use Your Information</h2>
                        <p className="mb-4">We use your information to:</p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>Provide and maintain our services</li>
                            <li>Process payments and transactions</li>
                            <li>Send you updates and notifications</li>
                            <li>Improve our platform and user experience</li>
                            <li>Prevent fraud and ensure security</li>
                            <li>Comply with legal obligations</li>
                        </ul>
                    </section>

                    {/* Third-Party Services */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">4. Third-Party Services</h2>
                        <p className="mb-4">We use the following third-party services:</p>

                        <div className="space-y-4">
                            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60">
                                <h4 className="font-semibold text-white mb-2">Supabase</h4>
                                <p className="text-sm text-zinc-400">Database and authentication services</p>
                            </div>

                            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60">
                                <h4 className="font-semibold text-white mb-2">Razorpay</h4>
                                <p className="text-sm text-zinc-400">Payment processing (PCI DSS compliant)</p>
                            </div>

                            <div className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60">
                                <h4 className="font-semibold text-white mb-2">Cloudflare R2</h4>
                                <p className="text-sm text-zinc-400">Secure file storage for audio content</p>
                            </div>
                        </div>
                    </section>

                    {/* Data Security */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">5. Data Security</h2>
                        <p className="mb-4">
                            We implement appropriate technical and organizational security measures to protect your personal information. However, no method of transmission over the internet is 100% secure, and we cannot guarantee absolute security.
                        </p>
                        <p>
                            Payment information is processed securely by Razorpay and is not stored on our servers.
                        </p>
                    </section>

                    {/* Your Rights */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">6. Your Rights</h2>
                        <p className="mb-4">Under Indian law, you have the right to:</p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>Access your personal information</li>
                            <li>Correct inaccurate information</li>
                            <li>Request deletion of your data</li>
                            <li>Withdraw consent for data processing</li>
                            <li>Object to certain data processing activities</li>
                        </ul>
                        <p className="mt-4">
                            To exercise these rights, please contact us at the email address provided below.
                        </p>
                    </section>

                    {/* Cookies */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">7. Cookies and Tracking</h2>
                        <p className="mb-4">
                            We use cookies and similar tracking technologies to enhance your experience. You can control cookies through your browser settings, but disabling them may affect platform functionality.
                        </p>
                    </section>

                    {/* Data Retention */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">8. Data Retention</h2>
                        <p>
                            We retain your personal information only for as long as necessary to fulfill the purposes outlined in this policy, unless a longer retention period is required by law.
                        </p>
                    </section>

                    {/* Children's Privacy */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">9. Children's Privacy</h2>
                        <p>
                            Our services are not intended for individuals under 18 years of age. We do not knowingly collect personal information from children.
                        </p>
                    </section>

                    {/* Changes to Policy */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">10. Changes to This Policy</h2>
                        <p>
                            We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new policy on this page and updating the "Last updated" date.
                        </p>
                    </section>

                    {/* Contact */}
                    <section className="p-6 rounded-2xl bg-violet-600/10 border border-violet-500/20">
                        <h2 className="text-2xl font-bold text-white mb-4">11. Contact Us</h2>
                        <p className="mb-4">
                            If you have questions about this Privacy Policy or wish to exercise your rights, please contact us:
                        </p>
                        <div className="space-y-2 text-zinc-300">
                            <p><strong>Email:</strong> privacy@mixmint.in</p>
                            <p><strong>Address:</strong> India</p>
                        </div>
                    </section>

                </div>
            </div>
        </div>
    );
}
