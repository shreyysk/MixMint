export default function RefundPolicyPage() {
    return (
        <div className="min-h-screen pb-24">
            <div className="px-6 md:px-12 max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-12">
                    <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
                        Refund Policy
                    </h1>
                    <p className="text-zinc-500">
                        Last updated: February 4, 2026
                    </p>
                </div>

                {/* Content */}
                <div className="space-y-8 text-zinc-300 leading-relaxed font-bold">
                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">1. Digital Content Sale Policy</h2>
                        <p className="mb-4">
                            Due to the irrevocable nature of digital content downloads, MixMint generally operates a <strong>no-refund policy</strong> once a download has been initiated or a file has been accessed.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">2. Technical Failure Exceptions</h2>
                        <p className="mb-4">
                            We may issue a refund or store credit only if:
                        </p>
                        <ul className="list-disc list-inside space-y-2 text-zinc-400">
                            <li>The audio file is demonstrably corrupted or defective at the source.</li>
                            <li>A technical error on the MixMint platform prevented the download despite successful payment.</li>
                            <li>The content was significantly misrepresented by the DJ in the preview or metadata.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">3. Refund Request Process</h2>
                        <p className="mb-4">
                            To request a refund under the above exceptions, please contact our support team within <strong>7 days</strong> of the transaction.
                        </p>
                        <div className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800/60 mt-4">
                            <p className="text-sm">
                                <strong>Email Support:</strong> help@mixmint.in <br />
                                <strong>Required Info:</strong> Transaction ID, DJ Name, and description of the technical issue.
                            </p>
                        </div>
                    </section>

                    <section>
                        <h2 className="text-2xl font-bold text-white mb-4">4. Abuse of Policy</h2>
                        <p>
                            We reserve the right to refuse refunds if we detect an abuse of our systems, including repeated refund requests or fraudulent claims of technical failure.
                        </p>
                    </section>
                </div>
            </div>
        </div>
    );
}
