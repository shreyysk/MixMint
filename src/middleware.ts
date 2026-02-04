import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * MixMint Multi-Tenant Middleware
 * Handles custom domain resolution and internal rewrites.
 */
export async function middleware(request: NextRequest) {
    const url = request.nextUrl
    const hostname = request.headers.get('host') || ''

    // Define main app domains (including local dev)
    const mainDomains = [
        'mixmint.site',
        'www.mixmint.site',
        'localhost:3000',
        process.env.NEXT_PUBLIC_APP_URL?.replace('https://', '').replace('http://', ''),
    ].filter(Boolean)

    const isMainDomain = mainDomains.some((d) => hostname.includes(d!))

    // 1. If it's a main domain, continue normally
    if (isMainDomain) {
        return NextResponse.next()
    }

    // 2. If it's a custom domain, we need to map it to a DJ profile
    // In production, we'd use a light-weight lookup (e.g. Redis/Vercel Edge Config)
    // For now, we perform an internal rewrite to /_sites/[domain] which the app handles
    // Or more simply, rewrite to /dj/[slug] if we had the mapping.

    // Since we don't have an edge-compatible DB lookup in standard middleware without Supabase,
    // we'll rewrite to a special internal route that performs the lookup.
    // BUT: Next.js Middleware can call Supabase.

    // For Phase 8 MVP, we'll implement a simple rewrite logic.
    // The goal is to make customdomain.com/track/1 rewrite to mixmint.site/dj/[slug]/track/1

    // We'll use a search param or header to tell the downstream routes this is a custom domain request
    const response = NextResponse.rewrite(new URL(`/_custom_domain/${hostname}${url.pathname}`, request.url))
    return response
}

// See "Matching Paths" below to learn more
export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - api (API routes)
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         */
        '/((?!api|_next/static|_next/image|favicon.ico).*)',
    ],
}
