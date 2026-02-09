"use client";

import React from "react";
import Link from "next/link";
import { XCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { motion } from "framer-motion";

export default function PaymentFailedPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center max-w-md"
      >
        <div className="w-24 h-24 rounded-full bg-red-600/20 border-2 border-red-500 flex items-center justify-center mx-auto mb-6">
          <XCircle className="text-red-500" size={48} />
        </div>

        <h1 className="text-4xl font-black text-white uppercase italic tracking-tight mb-4">
          Payment Failed
        </h1>

        <p className="text-zinc-400 font-bold mb-8">
          Your payment could not be processed. Please try again or contact support if the issue persists.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button onClick={() => window.history.back()}>
            Try Again
          </Button>
          <Link href="/explore">
            <Button variant="outline">
              Back to Explore
            </Button>
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
