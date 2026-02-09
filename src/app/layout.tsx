import './globals.css'
import type { Metadata } from 'next'
import { Inter, Space_Grotesk as Space_Grotesk_Font } from 'next/font/google'
import PreviewBar from './components/PreviewBar'
import { PlayerProvider } from './context/PlayerContext'
import { SearchProvider } from './context/SearchContext'
import { UserProvider } from './context/UserContext'
import Footer from './components/Footer'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const spaceGrotesk = Space_Grotesk_Font({ subsets: ['latin'], variable: '--font-space-grotesk' })

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
      <body className={`${inter.variable} ${spaceGrotesk.variable} font-sans flex flex-col min-h-screen`}>
        <UserProvider>
          <SearchProvider>
            <PlayerProvider>
              <div className="flex-grow relative pb-20"> {/* Changed to flex-grow */}
                {children}
                <PreviewBar />
              </div>
              <Footer />
            </PlayerProvider>
          </SearchProvider>
        </UserProvider>
      </body>
    </html>
  )
}
