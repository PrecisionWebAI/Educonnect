import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type { AcademicYear } from "@/types";

// ============================================================
// The academic year - the context switch in the top bar
//
// One row per school academic year, 1 April -> 31 March. The dates are derived on
// the server from the name, so this file never sends a date: a school that typed
// "June to April" would be measuring a different year than the performance score
// and the chapter plan assume.
//
// Reading the current year is auth-only (every role needs the label); reading the
// full list is `settings.read`; opening/switching is `academic_year.manage` plus a
// role senior to the principal.
// ============================================================

/** The current academic year, or `null` when the school has not opened one. */
export async function getCurrentAcademicYear(): Promise<AcademicYear | null> {
    const payload = toCamel<{ academicYear: AcademicYear | null }>(
        await api.get("/settings/academic-years/current"),
    );
    return payload.academicYear ?? null;
}

/** Every academic year this school has opened, newest window first. */
export async function getAcademicYears(): Promise<AcademicYear[]> {
    return toCamel<AcademicYear[]>(await api.get("/settings/academic-years"));
}

/**
 * Open an academic year. `startYear` is the only input the button sends ("2026" ->
 * "2026-27", 1 Apr 2026 -> 31 Mar 2027); a later year stays non-current until
 * somebody switches to it.
 */
export async function openAcademicYear(startYear?: number): Promise<AcademicYear> {
    return toCamel<AcademicYear>(
        await api.post("/settings/academic-years", {
            start_year: startYear ?? null,
        }),
    );
}

/** Make one academic year the year the screens read. */
export async function setCurrentAcademicYear(yearId: string): Promise<AcademicYear> {
    return toCamel<AcademicYear>(
        await api.patch(`/settings/academic-years/${yearId}/current`),
    );
}
