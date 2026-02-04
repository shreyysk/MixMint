import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
  allowedDevOrigins: [
    "839777d4-0a43-447a-bbc1-69eb367d6aca-00-3cuba2v585ifr.riker.replit.dev",
    "127.0.0.1",
    "localhost",
  ],
};

export default nextConfig;
