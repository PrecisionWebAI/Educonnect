/**
 * The academic year THIS browser tab is looking at.
 *
 * The school's running year is decided by the calendar, never stored as "the year
 * somebody switched to". A user may look at another year (next year's plan, last year's
 * records); that choice lives only here - in this tab's session storage - and rides on
 * every API call as `X-Academic-Year`. Nothing is written on the server, so it cannot
 * change what anybody else sees, and it is forgotten when the tab closes or the user
 * signs in again: every sign-in starts on the running year.
 */

const KEY = "educonnect.academic-year";

let memory: string | null = null;

function read(): string | null {
    if (memory !== null) return memory;
    if (typeof window === "undefined") return null;
    try {
        memory = window.sessionStorage.getItem(KEY);
    } catch {
        memory = null;
    }
    return memory;
}

/** The year id the user chose to look at, or `null` for "the running year". */
export function getSelectedYearId(): string | null {
    return read() || null;
}

export function setSelectedYearId(id: string | null): void {
    memory = id;
    if (typeof window === "undefined") return;
    try {
        if (id) window.sessionStorage.setItem(KEY, id);
        else window.sessionStorage.removeItem(KEY);
    } catch {
        /* storage may be unavailable (private mode); the in-memory copy still works */
    }
}

/** The header to add to a request: empty when the running year is wanted. */
export function academicYearHeader(): Record<string, string> {
    const id = getSelectedYearId();
    return id ? { "X-Academic-Year": id } : {};
}
