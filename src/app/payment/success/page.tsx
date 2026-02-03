"use client";

import React from "react";
import Link from "next/link";
import { CheckCircle, Download } from "lucide-react";
import { Button } from "@/app/components/ui/Button";
import { motion } from "framer-motion";

export default function PaymentSuccessPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center max-w-md"
      >
        <div className="w-24 h-24 rounded-full bg-green-600/20 border-2 border-green-500 flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="text-green-500" size={48} />
        </div>

        <h1 className="text-4xl font-black text-white uppercase italic tracking-tight mb-4">
          Payment Successful!
        </h1>

        <p className="text-zinc-400 font-bold mb-8">
          Your purchase has been confirmed. Check your email for download links and receipt.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/dashboard">
            <Button className="gap-2">
              <Download size={18} />
              Go to Library
            </Button>
          </Link>
          <Link href="/explore">
            <Button variant="outline">
              Explore More
            </Button>
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
