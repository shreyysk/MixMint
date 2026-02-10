import './globals.css'
import type { Metadata } from 'next'
import { Inter, Space_Grotesk as Space_Grotesk_Font, Poppins, JetBrains_Mono } from 'next/font/google'
import { SearchProvider } from './context/SearchContext'
import { UserProvider } from './context/UserContext'
import Footer from '@/components/layout/Footer'
import { AuthProvider } from '@/lib/AuthContext'
import { Navbar } from '@/components/layout/Navbar'
import { LeftSidebar } from '@/components/layout/LeftSidebar'
import { MobileNav } from '@/components/layout/MobileNav'
import MaintenanceGuard from '@/components/features/auth/MaintenanceGuard'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const spaceGrotesk = Space_Grotesk_Font({ subsets: ['latin'], variable: '--font-space-grotesk' })
const poppins = Poppins({ weight: ['600', '700', '800'], subsets: ['latin'], variable: '--font-poppins' })
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-jetbrains' })

export const metadata: Metadata = {
  title: 'MixMint | The Professional DJ Music Marketplace',
  description: 'A premium, high-security platform designed for DJs to monetize their releases. Low commissions, instant payouts, and zero-piracy downloads.',
  keywords: ['DJ', 'Music Marketplace', 'Music Monetization', 'Secure Downloads', 'MixMint', 'DJ SaaS'],
  manifest: '/manifest.json',
  themeColor: '#8B5CF6',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'MixMint',
  },
  icons: {
    icon: [
      { url: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icons/icon-512x512.png', sizes: '512x512', type: 'image/png' }
    ],
    apple: [
      { url: '/icons/icon-152x152.png', sizes: '152x152', type: 'image/png' }
    ]
  },
  openGraph: {
    title: 'MixMint | The Professional DJ Music Marketplace',
    description: 'Empowering DJs with professional monetization and secure distribution tools.',
    url: 'https://mixmint.site',
    siteName: 'MixMint',
    images: [
      {
        url: '/og-image.jpg', // Placeholder, we'll generate this or user provides
        width: 1200,
        height: 630,
        alt: 'MixMint Marketplace Preview',
      }
    ],
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'MixMint | Monetize Your DJ Sets & Tracks',
    description: 'The secure, high-yield marketplace for professional DJ content.',
    images: ['/og-image.jpg'],
  },
  robots: {
    index: true,
    follow: true,
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${spaceGrotesk.variable} ${poppins.variable} ${jetbrainsMono.variable} font-sans flex flex-col min-h-screen bg-gradient-dark`}>
        <AuthProvider>
          <UserProvider>
            <SearchProvider>
              {/* Desktop Sidebar */}
              <div className="hidden md:block">
                <LeftSidebar />
              </div>

              {/* Main Content Area */}
              <div className="md:ml-60 flex flex-col min-h-screen">
                <Navbar />
                <main className="flex-grow relative pb-20 md:pb-8">
                  <MaintenanceGuard>
                    {children}
                  </MaintenanceGuard>
                </main>
                <Footer />
              </div>

              {/* Mobile Bottom Nav */}
              <MobileNav />
            </SearchProvider>
          </UserProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
