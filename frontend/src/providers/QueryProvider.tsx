"use client";

import { QueryClient, QueryClientProvider, type QueryClientConfig } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

// ============================================================
// QueryProvider — TanStack Query cache for all server state.
// Defaults: cached data renders instantly on revisit (no spinner),
// silent background refetch when stale.
// ============================================================

const QUERY_DEFAULTS: QueryClientConfig = {
    defaultOptions: {
        queries: {
            staleTime: 30_000, // fresh for 30s → revisit = instant render, zero network
            gcTime: 5 * 60_000, // keep unused cache entries for 5 min
            refetchOnWindowFocus: false,
            retry: 1,
        },
    },
};

export function QueryProvider({ children }: { children: ReactNode }) {
    // One client for the app's lifetime — created lazily (SSR-safe).
    const [client] = useState(() => new QueryClient(QUERY_DEFAULTS));
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
