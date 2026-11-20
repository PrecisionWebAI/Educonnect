"use client";

import { createContext, useContext } from "react";
import type { AcademicYear } from "@/types";

// ============================================================
// Academic-year context + hook (non-component exports live here
// so the provider file satisfies react-refresh).
// ============================================================

export interface AcademicYearContextValue {
    /** The year every screen reads; null when the school has not set one. */
    current: AcademicYear | null;
    isLoading: boolean;
    error: Error | null;
    /** The permission + senior-role rule, mirrored from the server. */
    canManage: boolean;
    /** Refetch the current year after an open/switch. */
    refresh: () => Promise<void>;
}

export const AcademicYearContext = createContext<AcademicYearContextValue | null>(
    null,
);

export function useAcademicYear(): AcademicYearContextValue {
    const context = useContext(AcademicYearContext);
    if (!context) {
        throw new Error("useAcademicYear must be used within AcademicYearProvider");
    }
    return context;
}
