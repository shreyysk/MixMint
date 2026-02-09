'use client';

import React from 'react';
import { ChevronLeft } from 'lucide-react';
import Link from 'next/link';

const RefundPolicyPage = () => {
    return (
        <div className="min-h-screen bg-mint-dark text-white font-sans">
            <header className="p-4 flex items-center">
                <Link href="/" className="flex items-center text-mint-primary hover:text-mint-accent transition-colors">
                    <ChevronLeft size={24} />
                    <span>Back to Home</span>
                </Link>
            </header>
            <main className="max-w-4xl mx-auto p-8">
                <h1 className="text-4xl font-bold font-display text-mint-primary mb-8">Refund Policy</h1>
                
                <div className="space-y-6 text-zinc-300">
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">1. Overview</h2>
                        <p>Due to the nature of digital products, we generally do not offer refunds. Once a digital file has been purchased and downloaded, it cannot be returned.</p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">2. Eligibility for a Refund</h2>
                        <p>We may consider refunds on a case-by-case basis under the following circumstances:</p>
                        <ul className="list-disc list-inside ml-4">
                            <li>The file is corrupted or fails to download after a reasonable number of attempts.</li>
                            <li>The content is significantly not as described.</li>
                        </ul>
                        <p>To be eligible, you must contact us within 7 days of your purchase.</p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">3. How to Request a Refund</h2>
                        <p>Please contact our support team at <a href="mailto:support@mixmint.com" className="text-mint-primary hover:underline">support@mixmint.com</a> with your order details and a description of the issue. We will review your request and get back to you as soon as possible.</p>
                    </section>
                </div>
            </main>
        </div>
    );
};

export default RefundPolicyPage;
