import type { AcademicYear } from "@/types";

/**
 * The academic-year control's rules, as pure functions.
 *
 * The repository has no component-test stack, so the parts worth testing - the
 * label, the next year to open, and who may manage - live here and are covered by
 * `node --test`.
 */

const SENIOR_ACADEMIC_YEAR_ROLES = new Set([
    "SCHOOL_ADMIN",
    "SYSTEM_ADMIN",
    "DIRECTOR",
    "ADMIN",
]);

export type AcademicYearChipState =
    | "current"
    | "missing-manager"
    | "missing-readonly";

/** The chip's words. The compact form is for narrow screens. */
export function academicYearLabel(
    current: AcademicYear | null,
    compact = false,
): string {
    if (current) return current.name;
    return compact ? "Not set" : "Academic year not set";
}

/** `2026` -> `2026-27`, the label the open button prints. */
export function academicYearLabelForStart(startYear: number): string {
    return `${startYear}-${String(startYear + 1).slice(-2)}`;
}

const MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
];

function dateLabel(value: string): string {
    const [year, month, day] = value.split("-");
    const index = Number(month) - 1;
    if (!year || !day || !MONTHS[index]) return value;
    return `${day.padStart(2, "0")} ${MONTHS[index]} ${year}`;
}

/** `01 Apr 2026 – 31 Mar 2027`, the date line under each year's name. */
export function academicYearRange(year: AcademicYear): string {
    return `${dateLabel(year.startDate)} – ${dateLabel(year.endDate)}`;
}

/**
 * The next year to open: one after the newest year the school has, or the year
 * containing today when none has been opened. April starts a new academic year.
 */
export function nextAcademicYearStart(
    years: readonly AcademicYear[],
    today = new Date(),
): number {
    const starts = years
        .map((year) => Number(year.name.slice(0, 4)))
        .filter((value) => Number.isFinite(value));
    if (starts.length > 0) return Math.max(...starts) + 1;
    return today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
}

/** The only year that may be opened while `current` is running. */
export function nextAcademicYearStartAfterCurrent(
    current: AcademicYear | null,
    today = new Date(),
): number {
    if (current) {
        const start = Number(current.name.slice(0, 4));
        if (Number.isFinite(start)) return start + 1;
    }
    return today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
}

/** The state the chip renders: current, or missing with/without a manager. */
export function academicYearChipState(
    current: AcademicYear | null,
    canManage: boolean,
): AcademicYearChipState {
    if (current) return "current";
    return canManage ? "missing-manager" : "missing-readonly";
}

/**
 * The product rule mirrored from the server: the permission **and** a role senior
 * to the principal. A stale grant must not put the switch in front of a principal.
 */
export function canManageAcademicYear(
    permissions: readonly string[] | null | undefined,
    roles: readonly string[] | null | undefined,
): boolean {
    const hasPermission = (permissions ?? []).includes("academic_year.manage");
    const senior = (roles ?? []).some((role) => SENIOR_ACADEMIC_YEAR_ROLES.has(role));
    return hasPermission && senior;
}
