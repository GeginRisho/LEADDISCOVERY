import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/dashboard", destination: "/" },
      { source: "/tasks", destination: "/history" },
      { source: "/tasks/new", destination: "/scrape" },
    ];
  },
};

export default nextConfig;
