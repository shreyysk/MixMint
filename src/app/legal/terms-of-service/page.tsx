'use client';

import React from 'react';
import { ChevronLeft } from 'lucide-react';
import Link from 'next/link';

const TermsOfServicePage = () => {
    return (
        <div className="min-h-screen bg-mint-dark text-white font-sans">
            <header className="p-4 flex items-center">
                <Link href="/" className="flex items-center text-mint-primary hover:text-mint-accent transition-colors">
                    <ChevronLeft size={24} />
                    <span>Back to Home</span>
                </Link>
            </header>
            <main className="max-w-4xl mx-auto p-8">
                <h1 className="text-4xl font-bold font-display text-mint-primary mb-8">Terms of Service</h1>
                
                <div className="space-y-6 text-zinc-300">
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">1. Acceptance of Terms</h2>
                        <p>By accessing or using MixMint, you agree to be bound by these Terms of Service and our Privacy Policy. If you do not agree to these terms, please do not use our services.</p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">2. Description of Service</h2>
                        <p>MixMint provides a platform for DJs and music producers to sell their digital audio content directly to fans. This includes single tracks, music packs, and exclusive fan-only content.</p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">3. User Accounts</h2>
                        <p>You may be required to create an account to access certain features. You are responsible for maintaining the confidentiality of your account information and for all activities that occur under your account.</p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">4. Intellectual Property</h2>
                        <p>Artists retain all rights to their content. By uploading to MixMint, you grant us a license to display, sell, and distribute your content. Users who purchase content are granted a limited license for personal use only.</p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">5. Prohibited Conduct</h2>
                        <p>You agree not to use the service for any illegal or unauthorized purpose, including but not limited to copyright infringement or other intellectual property violations. We reserve the right to terminate accounts that violate these terms.</p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">6. Limitation of Liability</h2>
                        <p>MixMint is provided "as is" without any warranties. We are not liable for any damages or losses resulting from your use of the service.</p>
                    </section>
                </div>
            </main>
        </div>
    );
};

export default TermsOfServicePage;
