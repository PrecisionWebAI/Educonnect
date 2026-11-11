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

//: Words a school writes in capitals wherever they appear: a board (CBSE), a
//: category (OBC), a stage (LKG), a school (ABC). The database stores every value
//: lower-case (`app/core/text.py` on the server), so these cannot be recognised
//: from their shape any more and are listed instead. A person's name is never in
//: here.
const ACRONYMS = new Set([
    "abc",
    "cbse",
    "icse",
    "igcse",
    "kv",
    "dps",
    "ncc",
    "obc",
    "ews",
    "lkg",
    "ukg",
    "sst",
]);

//: Two-letter codes that are an acronym **only as the whole value**: "sc" is a
//: category, but the "st" in "st mary's road" is a street. Uppercased when the
//: value is exactly one of these and nothing else, so a dropdown option
//: ("SC") still matches what was stored while an address keeps its "St".
const SHORT_CODES = new Set(["sc", "st", "ib", "cs", "pe"]);

//: A blood group: "ab+" → "AB+", "o-" → "O-".
const BLOOD_GROUP = /^[ab]{1,2}[+-]$/;

//: An income band: "20k" → "20K", "1l" → "1L".
const INCOME_BAND = /^\d+[kl]$/;

/**
 * A value as it should be displayed, in Title Case: "prashant saxena" →
 * "Prashant Saxena", "delhi public school" → "Delhi Public School".
 *
 * The database holds canonical lower-case text (see `app/core/text.py` on the
 * server) and *this* is where presentation happens - so a name, a class
 * ("class 10-a" → "Class 10-A"), a subject or an address reads the way a school
 * writes it. Acronyms are kept whole ("abc school" → "ABC School", "obc" →
 * "OBC"), blood groups and income bands keep their capitals ("ab+" → "AB+",
 * "20k" → "20K"), and the separators a value actually uses - spaces, hyphens,
 * "&" - are preserved as they were. Anything empty comes back as "".
 *
 * A value that comes from a dropdown comes back **exactly** as the option is
 * spelled, which is what keeps a saved row preselecting its option when the form
 * is reopened.
 */
export function titleCase(value: string | null | undefined): string {
    const text = (value ?? "").trim();
    if (!text) return "";
    if (SHORT_CODES.has(text.toLowerCase())) return text.toUpperCase();
    return text
        .split(/(\s+)/)
        .map((chunk) => (chunk.trim() ? titleCaseToken(chunk) : chunk))
        .join("");
}

/** One whitespace-delimited token: "co-ed" → "Co-Ed", "ABC" → "ABC". */
function titleCaseToken(token: string): string {
    const lowered = token.toLowerCase();
    if (ACRONYMS.has(lowered) || BLOOD_GROUP.test(lowered) || INCOME_BAND.test(lowered)) {
        return token.toUpperCase();
    }
    return token
        .split(/([-&/])/)
        .map((part) => {
            if (/^[-&/]$/.test(part)) return part;
            if (ACRONYM.test(part)) return part;
            return part.charAt(0).toUpperCase() + part.slice(1).toLowerCase();
        })
        .join("");
}

// ============================================================
// Phone numbers
// ============================================================

/** How many digits a phone number has - the database stores exactly this many. */
export const PHONE_DIGITS = 10;

/**
 * The digits of a phone number, however it was typed: "+91 98765 43210",
 * "098765 43210" and "9876543210" all come back as "9876543210" (formatting and
 * the country / trunk prefix are dropped). Mirrors `phone_digits` in
 * `app/core/text.py`, which stores the value this way.
 */
export function phoneDigits(value: string | null | undefined): string {
    const digits = (value ?? "").replace(/\D/g, "");
    if (digits.length === 12 && digits.startsWith("91")) return digits.slice(2);
    if (digits.length === 11 && digits.startsWith("0")) return digits.slice(1);
    return digits;
}

/**
 * Why this phone number cannot be saved, or `null` when it is fine.
 *
 * Empty is not a problem here - whether a number is *required* is the form's own
 * rule (`missingRequiredFields` / `missingHireFields`). The server refuses a
 * number that is not ten digits (`phone_problem` in `app/core/text.py`); this
 * copy only saves the round-trip.
 */
export function phoneProblem(
    value: string | null | undefined,
    label = "Phone number",
): string | null {
    const text = (value ?? "").trim();
    if (!text) return null;
    const digits = phoneDigits(text);
    if (digits.length !== PHONE_DIGITS) {
        return `${label} must be exactly ${PHONE_DIGITS} digits - "${text}" has ${digits.length}.`;
    }
    return null;
}
