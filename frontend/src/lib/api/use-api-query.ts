"use client";

import { useQuery, type UseQueryOptions, type UseQueryResult } from "@tanstack/react-query";

// ============================================================
// useApiQuery — thin wrapper over TanStack Query for the app's
// service-layer fetchers. Keys follow ["resource", ...params].
// ============================================================

export function useApiQuery<T>(
    key: readonly unknown[],
    fetcher: () => Promise<T>,
    options?: Omit<UseQueryOptions<T, Error, T, readonly unknown[]>, "queryKey" | "queryFn">,
): UseQueryResult<T, Error> {
    return useQuery<T, Error>({ queryKey: key, queryFn: fetcher, ...options });
}
