"use client";

import { useCallback, useMemo, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useApiQuery } from "@/lib/api/use-api-query";
import { canManageAcademicYear } from "@/lib/academic-year/view";
import { getCurrentAcademicYear } from "@/services";
import { useAuth } from "@/providers/auth-context";

import {
    AcademicYearContext,
    type AcademicYearContextValue,
} from "./academic-year-context";

/**
 * Holds the one academic year every screen reads.
 *
 * The current-year read is auth-only on the server, so this provider is the single
 * query behind the navbar label and page guards. Opening/switching a year
 * invalidates the whole cache in `AcademicYearSelect`; this provider's query is
 * invalidated with the rest, so the chip never keeps the old year.
 */
export function AcademicYearProvider({ children }: { children: ReactNode }) {
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const query = useApiQuery(
        ["academic-year", "current"],
        getCurrentAcademicYear,
        // A platform admin has no school until they choose one. The API answers
        // `null` for that session; not asking keeps "not set" from rendering
        // before the school-selection banner has had its say.
        { enabled: Boolean(user?.schoolId) },
    );

    const refresh = useCallback(async () => {
        await queryClient.invalidateQueries({ queryKey: ["academic-year"] });
    }, [queryClient]);

    const value = useMemo<AcademicYearContextValue>(
        () => ({
            current: query.data ?? null,
            isLoading: query.isLoading,
            error: query.error ?? null,
            canManage: canManageAcademicYear(user?.permissions, user?.roles),
            refresh,
        }),
        [query.data, query.error, query.isLoading, refresh, user?.permissions, user?.roles],
    );

    return (
        <AcademicYearContext.Provider value={value}>
            {children}
        </AcademicYearContext.Provider>
    );
}
