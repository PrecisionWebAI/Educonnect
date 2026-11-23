import type { CatalogClass, PromotionResult } from "@/types";

/**
 * Where a class's students go next year, read from the school's own class order.
 *
 * Pure helpers (no React, no network) so the rules the Promote button follows - "the
 * next class by level", "the highest class completes instead" - can be tested alone.
 */

/** The class right after `className` by level, or `null` for the highest class. */
/** Class names compare without caring about capitals ("Class 6" = "class 6"). */
const same = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();

export function nextClassOf(classes: CatalogClass[], className: string): CatalogClass | null {
    const ordered = [...classes].sort((a, b) => a.level - b.level);
    const index = ordered.findIndex((item) => same(item.name, className));
    if (index < 0 || index + 1 >= ordered.length) return null;
    return ordered[index + 1];
}

/** The class right below `className` by level, or `null` for the lowest class. */
export function lowerClassOf(classes: CatalogClass[], className: string): CatalogClass | null {
    const ordered = [...classes].sort((a, b) => a.level - b.level);
    const index = ordered.findIndex((item) => same(item.name, className));
    return index > 0 ? ordered[index - 1] : null;
}

/** True when nothing comes after `className` - its students complete instead. */
export function isHighestClass(classes: CatalogClass[], className: string): boolean {
    return (
        classes.some((item) => same(item.name, className)) &&
        nextClassOf(classes, className) === null
    );
}

/** Every class **above** the student's own - promotion only ever goes up. */
export function higherClasses(classes: CatalogClass[], className: string): CatalogClass[] {
    const current = classes.find((item) => same(item.name, className));
    if (!current) return [];
    return [...classes]
        .sort((a, b) => a.level - b.level)
        .filter((item) => item.level > current.level);
}

/** "3 students" / "1 student". */
export function studentsLabel(count: number): string {
    return `${count} student${count === 1 ? "" : "s"}`;
}

/** One sentence for the toast: what was done and what was left alone, with the reasons. */
export function resultMessage(verb: string, result: PromotionResult): string {
    const head = result.done > 0 ? `${studentsLabel(result.done)} ${verb}.` : `Nobody was ${verb}.`;
    if (result.skipped.length === 0) return head;
    const reasons = result.skipped
        .slice(0, 3)
        .map((row) => `${row.name}: ${row.reason}`)
        .join(" ");
    const more = result.skipped.length > 3 ? ` (+${result.skipped.length - 3} more)` : "";
    return `${head} Skipped ${result.skipped.length} - ${reasons}${more}`;
}

/** What was done to a student's enrollment, read from the row the table already has. */
export type DoneKind = "promoted" | "retained" | "moved" | null;

export function doneKindOf(row: {
    nextYearOutcome?: string | null;
    movedFrom?: string | null;
}): DoneKind {
    const outcome = (row.nextYearOutcome ?? "").toLowerCase();
    if (outcome.startsWith("promoted")) return "promoted";
    if (outcome.startsWith("retained")) return "retained";
    if (row.movedFrom) return "moved";
    return null;
}

/** The label of a button that may instead take the earlier action back. */
export function undoLabel(
    rows: { nextYearOutcome?: string | null; movedFrom?: string | null }[],
    kind: DoneKind,
    base: string,
): string {
    if (rows.length === 0 || kind === null) return base;
    return rows.every((row) => doneKindOf(row) === kind) ? `Undo ${base.toLowerCase()}` : base;
}

/** The slice of an academic year this rule needs. */
export interface YearWindow {
    name: string;
    startDate: string;
    endDate: string;
}

function dayAfter(iso: string): string {
    const next = new Date(`${iso}T00:00:00Z`);
    next.setUTCDate(next.getUTCDate() + 1);
    return next.toISOString().slice(0, 10);
}

/**
 * Why students cannot be promoted or retained from the year on screen - or `null`.
 *
 * They move into the **next** session, so it has to exist first. Only one year after
 * the year that is really running can ever be created: looking at the running year the
 * answer is "create it from the year menu"; looking at any other year there is nothing
 * to create from here.
 */
export function nextYearBlock(
    years: YearWindow[],
    viewed: YearWindow | null | undefined,
    today: string,
): string | null {
    if (!viewed) return null;
    if (years.some((year) => year.startDate === dayAfter(viewed.endDate))) return null;
    const startYear = Number(viewed.startDate.slice(0, 4)) + 1;
    const label = `${startYear}-${String((startYear + 1) % 100).padStart(2, "0")}`;
    const running = viewed.startDate <= today && today <= viewed.endDate;
    return running
        ? `The next session (${label}) is not created yet, so students cannot be promoted or retained. Create ${label} from the year menu first.`
        : `The session after ${viewed.name} cannot be created yet: only one year after the running year can be opened, so students cannot be promoted or retained from here.`;
}
