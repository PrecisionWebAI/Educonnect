// ============================================================
// Shared display formatters used by the module pages.
// ============================================================

/** Formats a number as Indian rupees, e.g. 54600 -> "₹54,600". */
export function inr(n: number): string {
    return "₹" + n.toLocaleString("en-IN");
}

/** Today as `YYYY-MM-DD` (matches the date strings coming from the API). */
export function todayISO(): string {
    return new Date().toISOString().slice(0, 10);
}

/** `YYYY-MM-DD` for a date `days` from today — used for scheduling. */
export function isoInDays(days: number): string {
    return new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10);
}

//: A short word in capitals is an acronym, not shouting: ABC, DPS, KV.
const ACRONYM = /^[A-Z]{2,4}$/;

/**
 * A name as it should be displayed, in Title Case: "DELHI PUBLIC SCHOOL" →
 * "Delhi Public School", "delhi public school" → "Delhi Public School".
 *
 * Acronyms are left alone ("ABC School" stays "ABC School"), and the separators a
 * school name actually uses — spaces, hyphens, "&" — are preserved as they were.
 * Anything empty comes back as "".
 */
export function titleCase(value: string | null | undefined): string {
    const text = (value ?? "").trim();
    if (!text) return "";
    return text
        .split(/(\s+)/)
        .map((chunk) => (chunk.trim() ? titleCaseToken(chunk) : chunk))
        .join("");
}

/** One whitespace-delimited token: "co-ed" → "Co-Ed", "ABC" → "ABC". */
function titleCaseToken(token: string): string {
    return token
        .split(/([-&/])/)
        .map((part) => {
            if (/^[-&/]$/.test(part)) return part;
            if (ACRONYM.test(part)) return part;
            return part.charAt(0).toUpperCase() + part.slice(1).toLowerCase();
        })
        .join("");
}
