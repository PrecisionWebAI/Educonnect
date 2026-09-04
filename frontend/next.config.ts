import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    /* Disable auto-generating AGENTS.md and CLAUDE.md */
    agentRules: false,
};

export default nextConfig;
