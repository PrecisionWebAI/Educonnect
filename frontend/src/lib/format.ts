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
