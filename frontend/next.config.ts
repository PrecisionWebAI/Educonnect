import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    /* Disable auto-generating AGENTS.md and CLAUDE.md */
    agentRules: false,
    /**
     * Browser requests stay on the frontend's origin (`/api/...`) and Next's
     * server proxies them to the backend. That is what makes the app work over
     * localhost, a LAN IP and a tunnel without the browser needing to reach
     * port 8000 itself or pass a CORS preflight.
     *
     * A deployment with a separate API can set `API_PROXY_TARGET` on the Next
     * server; it defaults to the local compose backend.
     */
    async rewrites() {
        const target = (
            process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000"
        ).replace(/\/+$/, "");
        return [{ source: "/api/:path*", destination: `${target}/:path*` }];
    },
};

export default nextConfig;
