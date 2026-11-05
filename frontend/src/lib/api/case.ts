// ============================================================
// JSON key-case bridge — snake_case (API) <-> camelCase (UI)
//
// The backend speaks the database's language: every response body uses
// snake_case field names (`student_first_name`, `paid_on`), because the
// Pydantic/SQLModel schemas are named after the columns. The UI types in
// `@/types` are camelCase.
//
// Rather than hand-writing a 45-field mapper per screen (and risking one
// silently forgotten field), the Operations services wrap their payloads:
//
//     const row = toCamel<AdmissionApplicationRow>(await api.get(path));
//     await api.post(path, toSnake(values));
//
// Keys are converted; a value under one of `TITLE_CASE_KEYS` is also rendered in
// Title Case (the database stores lower-case text - see the note on that list),
// everything else passes through untouched. `null` / `undefined` survive, so
// optional fields such as a missing separation record stay absent instead of
// becoming `{}`.
// ============================================================

import { titleCase } from "@/lib/format";

type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

/**
 * Response fields whose value is **display text**, so it is rendered in Title
 * Case on the way in.
 *
 * The database stores canonical lower-case text (`app/core/text.py` on the
 * server) and the UI decides how it looks. Doing it here, once, means every
 * table, card, dropdown and detail view shows "Prashant Saxena" / "Class 10-A" /
 * "CBSE" without `titleCase(...)` repeated at a few hundred call sites - and it
 * also keeps the values comparable: a form's option list ("Class 9") and a row
 * read back from the API now agree on the spelling.
 *
 * Matched on the key with underscores removed and lower-cased, so `class_name`
 * and `className` are the same entry. Only presentation belongs here:
 *
 * * an **identifier** (`application_no`, `employee_code`, `ifsc`, `isbn`) is left
 *   exactly as stored - title-casing "ADM-2026-0001" would corrupt it;
 * * an **email / phone / url** is not a name;
 * * a **status or codename** ("Draft", "school_admin", "Yes") is a value the
 *   workflow compares, so its spelling is not ours to change;
 * * **prose** (a note, a reason, a question, a description) would only look wrong.
 *
 * `subject` is the one key that is both a vocabulary word and a sentence: it is a
 * subject name ("mathematics" → "Mathematics") on the academics screens and the
 * subject *line* of a support ticket. Title-casing a ticket line reads fine, so
 * one entry serves both rather than two rules nobody would remember.
 */
const TITLE_CASE_KEYS = new Set(
    [
        "name",
        "fullName",
        "firstName",
        "middleName",
        "lastName",
        "studentName",
        "guardianName",
        "guardian",
        "guardianRelation",
        "fatherName",
        "motherName",
        "teacherName",
        "classTeacher",
        "assignedBy",
        "staff",
        "student",
        "reporter",
        "schoolName",
        "className",
        "classLabel",
        "classroomRemoved",
        "separationDroppedClass",
        "section",
        "sectionName",
        "subject",
        "subjectName",
        "department",
        "designation",
        "religion",
        "motherTongue",
        "category",
        "nationality",
        "bloodGroup",
        "gender",
        "relation",
        "relationshipType",
        "board",
        "previousBoard",
        "previousSchoolName",
        "previousClassPassed",
        "currentClassOrLastClass",
        "appliedForClassLevel",
        "appliedSectionPreference",
        "occupation",
        "fatherOccupation",
        "motherOccupation",
        "guardianOccupation",
        "annualIncome",
        "fatherAnnualIncome",
        "motherAnnualIncome",
        "bankName",
        "transportRoute",
        "route",
        "driver",
        "address",
        "permanentAddress",
        "guardianAddress",
        "city",
        "state",
        "country",
        "stage",
        "day",
        "month",
        "term",
        "grade",
        "exam",
        "examType",
        "author",
        "room",
        "withWhom",
        "book",
    ].map((key) => key.replace(/_/g, "").toLowerCase()),
);

function isTitleKey(convertedKey: string): boolean {
    return TITLE_CASE_KEYS.has(convertedKey.replace(/_/g, "").toLowerCase());
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function toCamelKey(key: string): string {
    return key.replace(/_([a-z0-9])/g, (_, char: string) => char.toUpperCase());
}

function toSnakeKey(key: string): string {
    return key.replace(/[A-Z]/g, (char) => `_${char.toLowerCase()}`);
}

function convert(value: unknown, key: (k: string) => string): unknown {
    if (Array.isArray(value)) return value.map((item) => convert(item, key));
    if (!isPlainObject(value)) return value;
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
        out[key(k)] = convert(v, key);
    }
    return out;
}

/** Recursively renames every object key from `snake_case` to `camelCase`. */
export function toCamel<T>(value: unknown): T {
    return convert(value, toCamelKey) as T;
}

/** Recursively renames every object key from `camelCase` to `snake_case`. */
export function toSnake<T = unknown>(value: unknown): T {
    return convert(value, toSnakeKey) as T;
}

function titleValues(value: unknown, title: boolean): unknown {
    if (Array.isArray(value)) return value.map((item) => titleValues(item, title));
    if (isPlainObject(value)) {
        const out: Record<string, unknown> = {};
        for (const [k, v] of Object.entries(value)) {
            out[k] = titleValues(v, title && isTitleKey(k));
        }
        return out;
    }
    if (title && typeof value === "string") return titleCase(value);
    return value;
}

/**
 * The same walk, but over **values**: every string under a `TITLE_CASE_KEYS` key
 * comes back in Title Case, keys untouched.
 *
 * The API client applies this to every response body, so a screen shows
 * "Prashant Saxena" / "Class 10-A" / "CBSE" whether it reads the row through
 * `toCamel` or maps the fields by hand.
 */
export function titleCaseValues<T>(value: unknown): T {
    return titleValues(value, true) as T;
}

/** Type-only re-export so callers can talk about the JSON shape if needed. */
export type { Json };
