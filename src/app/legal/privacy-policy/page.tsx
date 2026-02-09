'use client';

import React from 'react';
import { ChevronLeft } from 'lucide-react';
import Link from 'next/link';

const PrivacyPolicyPage = () => {
    return (
        <div className="min-h-screen bg-mint-dark text-white font-sans">
            <header className="p-4 flex items-center">
                <Link href="/" className="flex items-center text-mint-primary hover:text-mint-accent transition-colors">
                    <ChevronLeft size={24} />
                    <span>Back to Home</span>
                </Link>
            </header>
            <main className="max-w-4xl mx-auto p-8">
                <h1 className="text-4xl font-bold font-display text-mint-primary mb-8">Privacy Policy</h1>
                
                <div className="space-y-6 text-zinc-300">
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">1. Information We Collect</h2>
                        <p>We collect information you provide directly to us, such as when you create an account, purchase content, or contact us for support. This may include your name, email address, and payment information.</p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">2. How We Use Your Information</h2>
                        <p>We use your information to provide and improve our services, process transactions, communicate with you, and ensure the security of our platform.</p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">3. Information Sharing</h2>
                        <p>We do not sell your personal information. We may share information with third-party service providers for functions like payment processing and analytics, or if required by law.</p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">4. Data Security</h2>
                        <p>We implement security measures to protect your information, but no system is completely secure. We cannot guarantee the absolute security of your data.</p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">5. Your Choices</h2>
                        <p>You can review and update your account information at any time. You may also opt-out of promotional communications by following the instructions in those messages.</p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">6. Changes to This Policy</h2>
                        <p>We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new policy on this page.</p>
                    </section>
                </div>
            </main>
        </div>
    );
};

export default PrivacyPolicyPage;
