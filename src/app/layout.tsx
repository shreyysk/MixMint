import type { Metadata } from "next";
import { Inter, Fira_Code } from "next/font/google";
import "./styles/globals.css";
import { Navbar } from "@/app/components/Navbar";
import { Footer } from "@/app/components/Footer";
import { AuthProvider } from "@/app/lib/AuthContext";
import { ReferralTracker } from "@/app/components/rewards/ReferralTracker";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const firaCode = Fira_Code({
  variable: "--font-fira-code",
  subsets: ["latin"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "MixMint — Home of DJ Releases",
  description: "Buy tracks, subscribe to DJs, and access exclusive drops.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${firaCode.variable} antialiased`}
      >
        <AuthProvider>
          <ReferralTracker />
          <div className="flex flex-col min-h-screen">
            <Navbar />
            <main className="flex-grow page-pt">
              {children}
            </main>
            <Footer />
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
