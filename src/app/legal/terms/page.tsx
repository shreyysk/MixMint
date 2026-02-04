export default function TermsOfServicePage() {
    return (
        <div className="min-h-screen pb-24">
            <div className="px-6 md:px-12 max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-12">
                    <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
                        Terms of Service
                    </h1>
                    <p className="text-zinc-500">
                        Last updated: February 4, 2026
                    </p>
                </div>

                {/* Content */}
                <div className="space-y-8 text-zinc-300 leading-relaxed">

                    {/* Introduction */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">1. Acceptance of Terms</h2>
                        <p className="mb-4">
                            By accessing or using MixMint ("Platform," "Service," "we," "our," or "us"), you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our Platform.
                        </p>
                        <p>
                            These terms are governed by the laws of India and subject to the jurisdiction of Indian courts.
                        </p>
                    </section>

                    {/* Eligibility */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">2. Eligibility</h2>
                        <p className="mb-4">
                            You must be at least 18 years old to use this Platform. By using our services, you represent and warrant that you meet this age requirement.
                        </p>
                    </section>

                    {/* User Accounts */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">3. User Accounts</h2>

                        <h3 className="text-xl font-semibold text-white mb-3">3.1 Account Creation</h3>
                        <p className="mb-4">
                            You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account.
                        </p>

                        <h3 className="text-xl font-semibold text-white mb-3">3.2 Account Types</h3>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li><strong>Fan Accounts:</strong> For purchasing and downloading music</li>
                            <li><strong>DJ Accounts:</strong> For uploading and selling music content</li>
                        </ul>
                    </section>

                    {/* DJ Responsibilities */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">4. DJ Responsibilities</h2>
                        <p className="mb-4">As a DJ on our Platform, you agree to:</p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>Upload only content you own or have rights to distribute</li>
                            <li>Provide accurate metadata and pricing information</li>
                            <li>Not upload copyrighted material without proper authorization</li>
                            <li>Comply with all applicable laws regarding music distribution</li>
                            <li>Not engage in fraudulent or deceptive practices</li>
                        </ul>
                    </section>

                    {/* Content Ownership */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">5. Content Ownership and Licensing</h2>

                        <h3 className="text-xl font-semibold text-white mb-3">5.1 DJ Content</h3>
                        <p className="mb-4">
                            DJs retain all ownership rights to their uploaded content. By uploading content, you grant MixMint a non-exclusive license to store, distribute, and display your content on the Platform.
                        </p>

                        <h3 className="text-xl font-semibold text-white mb-3">5.2 Purchased Content</h3>
                        <p className="mb-4">
                            When you purchase content, you receive a personal, non-transferable license to download and use the content for personal, non-commercial purposes. You do not acquire ownership of the underlying intellectual property.
                        </p>

                        <h3 className="text-xl font-semibold text-white mb-3">5.3 Prohibited Uses</h3>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>Reselling or redistributing purchased content</li>
                            <li>Using content for commercial purposes without permission</li>
                            <li>Removing or altering copyright notices</li>
                            <li>Sharing download links with unauthorized parties</li>
                        </ul>
                    </section>

                    {/* Payments */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">6. Payments and Pricing</h2>

                        <h3 className="text-xl font-semibold text-white mb-3">6.1 Payment Processing</h3>
                        <p className="mb-4">
                            All payments are processed securely through Razorpay. We do not store your payment card information. By making a purchase, you agree to Razorpay's terms and conditions.
                        </p>

                        <h3 className="text-xl font-semibold text-white mb-3">6.2 Pricing</h3>
                        <p className="mb-4">
                            All prices are listed in Indian Rupees (INR) and include applicable taxes. DJs set their own pricing for content.
                        </p>

                        <h3 className="text-xl font-semibold text-white mb-3">6.3 Subscriptions</h3>
                        <p className="mb-4">
                            Subscription plans provide monthly access to DJ content. Subscriptions auto-renew unless cancelled before the renewal date. See our Refund Policy for cancellation terms.
                        </p>
                    </section>

                    {/* Prohibited Activities */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">7. Prohibited Activities</h2>
                        <p className="mb-4">You may not:</p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>Violate any applicable laws or regulations</li>
                            <li>Infringe on intellectual property rights</li>
                            <li>Upload malicious code or viruses</li>
                            <li>Attempt to gain unauthorized access to our systems</li>
                            <li>Engage in fraudulent transactions</li>
                            <li>Harass or abuse other users</li>
                            <li>Scrape or data mine the Platform</li>
                            <li>Impersonate others or misrepresent your identity</li>
                        </ul>
                    </section>

                    {/* Content Moderation */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">8. Content Moderation</h2>
                        <p className="mb-4">
                            We reserve the right to review, remove, or refuse any content that violates these Terms or is otherwise objectionable. We may suspend or terminate accounts that repeatedly violate our policies.
                        </p>
                    </section>

                    {/* Disclaimer */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">9. Disclaimer of Warranties</h2>
                        <p className="mb-4">
                            The Platform is provided "as is" and "as available" without warranties of any kind, either express or implied. We do not guarantee uninterrupted access or error-free operation.
                        </p>
                        <p>
                            We are not responsible for the quality, accuracy, or legality of content uploaded by DJs.
                        </p>
                    </section>

                    {/* Limitation of Liability */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">10. Limitation of Liability</h2>
                        <p className="mb-4">
                            To the maximum extent permitted by Indian law, MixMint shall not be liable for any indirect, incidental, special, consequential, or punitive damages arising from your use of the Platform.
                        </p>
                        <p>
                            Our total liability for any claim shall not exceed the amount you paid to us in the 12 months preceding the claim.
                        </p>
                    </section>

                    {/* Dispute Resolution */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">11. Dispute Resolution</h2>
                        <p className="mb-4">
                            Any disputes arising from these Terms shall be governed by Indian law and subject to the exclusive jurisdiction of courts in India.
                        </p>
                        <p>
                            We encourage users to contact us first to resolve disputes amicably before pursuing legal action.
                        </p>
                    </section>

                    {/* Termination */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">12. Termination</h2>
                        <p className="mb-4">
                            We may suspend or terminate your account at any time for violation of these Terms. You may close your account at any time by contacting us.
                        </p>
                        <p>
                            Upon termination, your right to access the Platform ceases immediately. Previously purchased content may remain accessible subject to our discretion.
                        </p>
                    </section>

                    {/* Changes to Terms */}
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">13. Changes to Terms</h2>
                        <p>
                            We reserve the right to modify these Terms at any time. We will notify users of material changes via email or platform notification. Continued use of the Platform after changes constitutes acceptance of the new Terms.
                        </p>
                    </section>

                    {/* Contact */}
                    <section className="p-6 rounded-2xl bg-violet-600/10 border border-violet-500/20">
                        <h2 className="text-2xl font-bold text-white mb-4">14. Contact Information</h2>
                        <p className="mb-4">
                            For questions about these Terms of Service, please contact us:
                        </p>
                        <div className="space-y-2 text-zinc-300">
                            <p><strong>Email:</strong> legal@mixmint.in</p>
                            <p><strong>Address:</strong> India</p>
                        </div>
                    </section>

                </div>
            </div>
        </div>
    );
}
