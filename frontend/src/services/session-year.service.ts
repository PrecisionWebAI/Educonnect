import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type { SessionYear } from "@/types";

// ============================================================
// The session year - the context switch in the top bar
//
// One row per school session, 1 April -> 31 March. The dates are **derived on the
// server** from the name, so this file never sends a date: a school that typed
// "June to April" would be measuring a different year than the performance score
// and the chapter plan assume.
//
// Reading is `settings.read` (the year is printed on most screens); opening or
// switching one is `academic_year.manage`, which is the office's decision.
// ============================================================

/** Every session this school has opened, newest window first. */
export async function getSessionYears(): Promise<SessionYear[]> {
    return toCamel<SessionYear[]>(await api.get("/settings/session-years"));
}

/**
 * Open a session. `startYear` is the only input the button sends ("2026" ->
 * "2026-27", 1 Apr 2026 -> 31 Mar 2027); a later year stays non-current until
 * somebody switches to it.
 */
export async function openSessionYear(startYear?: number): Promise<SessionYear> {
    return toCamel<SessionYear>(
        await api.post("/settings/session-years", {
            start_year: startYear ?? null,
        }),
    );
}

/** Make one session the year the screens read. */
export async function setCurrentSessionYear(yearId: string): Promise<SessionYear> {
    return toCamel<SessionYear>(await api.patch(`/settings/session-years/${yearId}/current`));
}
