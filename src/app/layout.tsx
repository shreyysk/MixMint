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

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const spaceGrotesk = Space_Grotesk_Font({ subsets: ['latin'], variable: '--font-space-grotesk' })
const poppins = Poppins({ weight: ['600', '700', '800'], subsets: ['latin'], variable: '--font-poppins' })
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-jetbrains' })

export const metadata: Metadata = {
  title: 'MixMint - Home of DJ Releases',
  description: 'A high-security, DJ-first monetization SaaS.',
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
                  {children}
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
