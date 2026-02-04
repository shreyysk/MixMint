# MixMint - DJ Music Marketplace

## Overview
MixMint is a Next.js 16 application that serves as a direct artist support platform for DJs. Users can buy tracks, subscribe to DJs, and access exclusive drops without streaming.

## Tech Stack
- **Framework**: Next.js 16.1.6 with Turbopack
- **Language**: TypeScript
- **Styling**: Tailwind CSS 4
- **Database**: Supabase (external PostgreSQL)
- **Authentication**: Supabase Auth
- **Payments**: Razorpay
- **Email**: Resend
- **File Storage**: AWS S3 / R2

## Project Structure
```
src/
  app/
    api/           # API routes
    admin/         # Admin dashboard pages
    album/         # Album detail pages
    albums/        # Albums listing
    auth/          # Authentication pages (login/signup)
    components/    # Reusable UI components
    contact/       # Contact page
    dashboard/     # User dashboard
    dj/            # DJ profiles and management
    explore/       # DJ exploration page
    legal/         # Legal pages
    lib/           # Utilities and shared libraries
    payment/       # Payment pages
    pricing/       # Pricing page
    styles/        # Global CSS
    track/         # Track detail pages
    tracks/        # Tracks listing
    layout.tsx     # Root layout
    page.tsx       # Landing page
```

## Environment Variables Required
- `NEXT_PUBLIC_SUPABASE_URL` - Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Supabase public API key

## Development
The app runs on port 5000 with the command:
```
npm run dev -- -p 5000 -H 0.0.0.0
```

## Key Features
- DJ profile management
- Track and album uploads
- Secure downloads
- DJ subscriptions
- Payment processing via Razorpay
- User authentication via Supabase

## Recent Changes
- 2026-02-04: Imported from GitHub and configured for Replit environment
  - Fixed Next.js 16 API route handlers to use Promise-based params
  - Removed legacy middleware (not compatible with Next.js 16)
  - Created root page.tsx for landing page
  - Configured Next.js to allow Replit dev origins

## Notes
- The middleware was removed as it's deprecated in Next.js 16 in favor of "proxy". Custom domain routing will need to be reimplemented if needed.
- The app uses Supabase for all database operations - make sure your Supabase project has the required tables.
