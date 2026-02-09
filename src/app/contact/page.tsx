"use client";

import { Mail, MessageSquare, CreditCard, HelpCircle, Twitter, Instagram, Github } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useState } from "react";

export default function ContactPage() {
    const [formData, setFormData] = useState({
        name: "",
        email: "",
        category: "general",
        message: ""
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        // UI only - no backend logic
        alert("This is a UI demonstration. In production, this would send your message to our support team.");
    };

    return (
        <div className="min-h-screen pb-24">
            <div className="px-6 md:px-12 max-w-6xl mx-auto">
                {/* Header */}
                <div className="mb-12 text-center">
                    <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
                        Contact & Support
                    </h1>
                    <p className="text-zinc-500 max-w-2xl mx-auto">
                        Have a question or need help? We're here to assist you. Choose your preferred contact method below.
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-16">
                    {/* Contact Information */}
                    <div className="space-y-6">
                        <h2 className="text-2xl font-bold text-white mb-6">Get in Touch</h2>

                        {/* Email Support */}
                        <div className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800/60 hover:border-violet-500/40 transition-all">
                            <div className="flex items-start gap-4">
                                <div className="w-12 h-12 rounded-xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center shrink-0">
                                    <Mail className="text-violet-400" size={20} />
                                </div>
                                <div>
                                    <h3 className="text-lg font-semibold text-white mb-2">Email Support</h3>
                                    <p className="text-zinc-400 text-sm mb-3">
                                        For general inquiries and support requests
                                    </p>
                                    <a href="mailto:support@mixmint.in" className="text-violet-400 hover:text-violet-300 font-medium text-sm">
                                        support@mixmint.in
                                    </a>
                                    <p className="text-zinc-600 text-xs mt-2">Response time: 24-48 hours</p>
                                </div>
                            </div>
                        </div>

                        {/* Payment Issues */}
                        <div className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800/60 hover:border-amber-500/40 transition-all">
                            <div className="flex items-start gap-4">
                                <div className="w-12 h-12 rounded-xl bg-amber-600/10 border border-amber-500/20 flex items-center justify-center shrink-0">
                                    <CreditCard className="text-amber-400" size={20} />
                                </div>
                                <div>
                                    <h3 className="text-lg font-semibold text-white mb-2">Payment & Billing</h3>
                                    <p className="text-zinc-400 text-sm mb-3">
                                        For payment issues, refunds, and billing questions
                                    </p>
                                    <a href="mailto:payments@mixmint.in" className="text-amber-400 hover:text-amber-300 font-medium text-sm">
                                        payments@mixmint.in
                                    </a>
                                    <p className="text-zinc-600 text-xs mt-2">Response time: 5-7 business days</p>
                                </div>
                            </div>
                        </div>

                        {/* Legal */}
                        <div className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800/60 hover:border-emerald-500/40 transition-all">
                            <div className="flex items-start gap-4">
                                <div className="w-12 h-12 rounded-xl bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center shrink-0">
                                    <HelpCircle className="text-emerald-400" size={20} />
                                </div>
                                <div>
                                    <h3 className="text-lg font-semibold text-white mb-2">Legal & Privacy</h3>
                                    <p className="text-zinc-400 text-sm mb-3">
                                        For legal matters, privacy concerns, and copyright issues
                                    </p>
                                    <a href="mailto:legal@mixmint.in" className="text-emerald-400 hover:text-emerald-300 font-medium text-sm">
                                        legal@mixmint.in
                                    </a>
                                    <p className="text-zinc-600 text-xs mt-2">Response time: 7-10 business days</p>
                                </div>
                            </div>
                        </div>

                        {/* Social Media */}
                        <div className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800/60">
                            <h3 className="text-lg font-semibold text-white mb-4">Follow Us</h3>
                            <p className="text-zinc-400 text-sm mb-4">
                                Stay updated with the latest news and releases
                            </p>
                            <div className="flex gap-3">
                                <a href="#" className="w-10 h-10 rounded-lg bg-zinc-800/60 border border-zinc-700/50 flex items-center justify-center text-zinc-500 hover:text-white hover:border-zinc-600 transition-all">
                                    <Twitter size={18} />
                                </a>
                                <a href="#" className="w-10 h-10 rounded-lg bg-zinc-800/60 border border-zinc-700/50 flex items-center justify-center text-zinc-500 hover:text-white hover:border-zinc-600 transition-all">
                                    <Instagram size={18} />
                                </a>
                                <a href="#" className="w-10 h-10 rounded-lg bg-zinc-800/60 border border-zinc-700/50 flex items-center justify-center text-zinc-500 hover:text-white hover:border-zinc-600 transition-all">
                                    <Github size={18} />
                                </a>
                            </div>
                        </div>
                    </div>

                    {/* Contact Form */}
                    <div>
                        <h2 className="text-2xl font-bold text-white mb-6">Send Us a Message</h2>
                        <form onSubmit={handleSubmit} className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800/60 space-y-5">

                            {/* Name */}
                            <div>
                                <label htmlFor="name" className="block text-sm font-medium text-zinc-300 mb-2">
                                    Your Name
                                </label>
                                <input
                                    type="text"
                                    id="name"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full bg-zinc-800/60 border border-zinc-700/50 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-violet-500/50 transition-all placeholder:text-zinc-600"
                                    placeholder="John Doe"
                                    required
                                />
                            </div>

                            {/* Email */}
                            <div>
                                <label htmlFor="email" className="block text-sm font-medium text-zinc-300 mb-2">
                                    Email Address
                                </label>
                                <input
                                    type="email"
                                    id="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    className="w-full bg-zinc-800/60 border border-zinc-700/50 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-violet-500/50 transition-all placeholder:text-zinc-600"
                                    placeholder="john@example.com"
                                    required
                                />
                            </div>

                            {/* Category */}
                            <div>
                                <label htmlFor="category" className="block text-sm font-medium text-zinc-300 mb-2">
                                    Category
                                </label>
                                <select
                                    id="category"
                                    value={formData.category}
                                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                                    className="w-full bg-zinc-800/60 border border-zinc-700/50 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-violet-500/50 transition-all"
                                    required
                                >
                                    <option value="general">General Inquiry</option>
                                    <option value="technical">Technical Support</option>
                                    <option value="billing">Billing & Payments</option>
                                    <option value="content">Content Issues</option>
                                    <option value="dj">DJ Account</option>
                                    <option value="other">Other</option>
                                </select>
                            </div>

                            {/* Message */}
                            <div>
                                <label htmlFor="message" className="block text-sm font-medium text-zinc-300 mb-2">
                                    Message
                                </label>
                                <textarea
                                    id="message"
                                    value={formData.message}
                                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                                    rows={6}
                                    className="w-full bg-zinc-800/60 border border-zinc-700/50 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-violet-500/50 transition-all placeholder:text-zinc-600 resize-none"
                                    placeholder="Please describe your question or issue in detail..."
                                    required
                                />
                            </div>

                            {/* Submit Button */}
                            <Button type="submit" className="w-full" size="lg">
                                <MessageSquare size={18} />
                                Send Message
                            </Button>

                            <p className="text-xs text-zinc-600 text-center">
                                By submitting this form, you agree to our Privacy Policy
                            </p>
                        </form>
                    </div>
                </div>

                {/* FAQ Section */}
                <div className="p-8 rounded-2xl bg-gradient-to-br from-violet-600/10 to-indigo-600/10 border border-violet-500/20">
                    <h2 className="text-2xl font-bold text-white mb-4">Frequently Asked Questions</h2>
                    <p className="text-zinc-400 mb-6">
                        Before contacting us, you might find answers to common questions in our FAQ section.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <a href="/legal/refund-policy" className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60 hover:border-violet-500/40 transition-all group">
                            <h4 className="font-semibold text-white mb-2 group-hover:text-violet-400 transition-colors">How do refunds work?</h4>
                            <p className="text-sm text-zinc-500">Learn about our refund and cancellation policy</p>
                        </a>
                        <a href="/legal/payment-disclaimer" className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60 hover:border-violet-500/40 transition-all group">
                            <h4 className="font-semibold text-white mb-2 group-hover:text-violet-400 transition-colors">Payment methods?</h4>
                            <p className="text-sm text-zinc-500">See all accepted payment options</p>
                        </a>
                        <a href="/legal/terms" className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60 hover:border-violet-500/40 transition-all group">
                            <h4 className="font-semibold text-white mb-2 group-hover:text-violet-400 transition-colors">Terms of Service</h4>
                            <p className="text-sm text-zinc-500">Read our complete terms and conditions</p>
                        </a>
                        <a href="/legal/privacy" className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800/60 hover:border-violet-500/40 transition-all group">
                            <h4 className="font-semibold text-white mb-2 group-hover:text-violet-400 transition-colors">Privacy & Data</h4>
                            <p className="text-sm text-zinc-500">How we handle your personal information</p>
                        </a>
                    </div>
                </div>

            </div>
        </div>
    );
}
