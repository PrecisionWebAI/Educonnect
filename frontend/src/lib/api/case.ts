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
// Keys are converted; values (strings, numbers, dates, enums-as-strings) are
// passed through untouched. `null` / `undefined` survive, so optional fields
// such as a missing separation record stay absent instead of becoming `{}`.
// ============================================================

type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

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

/** Type-only re-export so callers can talk about the JSON shape if needed. */
export type { Json };
