import type { CourseChapter, CourseSubject } from "@/types";

/**
 * The Course tab's rules, as **pure functions**.
 *
 * Same reason as `lib/attendance/view.ts`: the repository has no component-test stack,
 * so the parts worth testing (the bar's shares, the ahead/behind badge, who may tick)
 * live here and are covered by `node --test` instead of a browser.
 *
 * Nothing here decides **whether** a tick is allowed - the server does that and sends
 * `canTick` per chapter. These functions only turn that answer into words.
 */

/** One slice of the segmented bar: a teacher's finished chapters, or the remainder. */
export interface BarSegment {
    key: string;
    label: string;
    /** How many chapters this slice stands for. */
    chapters: number;
    /** Share of the whole plan (0-100, one decimal). */
    share: number;
    /** The palette slot for this slice. */
    tone: "violet" | "sky" | "amber" | "emerald" | "rose" | "slate";
}

/** The palette, in order. A teacher keeps their slot as long as the list is stable. */
const TONES: BarSegment["tone"][] = ["violet", "sky", "amber", "emerald", "rose"];

/**
 * The bar for one subject: one slice per teacher who finished something, then the grey
 * remainder ("not done").
 *
 * A teacher with 0 completed chapters gets **no slice** - an empty slice would be a
 * colour that stands for nothing - but they stay in the legend and in the row's teacher
 * list, which is where "they have not started" belongs. A subject with no plan returns
 * `[]` and the row prints "No plan yet" instead of an empty bar.
 */
export function barSegments(subject: CourseSubject): BarSegment[] {
    if (!subject.total) return [];

    const segments: BarSegment[] = [];
    const contributors = subject.teachers.filter((teacher) => teacher.completed > 0);
    contributors.forEach((teacher, index) => {
        segments.push({
            key: teacher.employeeId,
            label: teacher.name,
            chapters: teacher.completed,
            share: round1((teacher.completed / subject.total) * 100),
            tone: TONES[index % TONES.length],
        });
    });

    const done = contributors.reduce((sum, teacher) => sum + teacher.completed, 0);
    const remaining = Math.max(0, subject.total - done);
    if (remaining > 0) {
        segments.push({
            key: "remaining",
            label: "Not done",
            chapters: remaining,
            share: round1((remaining / subject.total) * 100),
            tone: "slate",
        });
    }
    return segments;
}

/** `2/10` - the hover text on a slice, and the row's own count. */
export function chaptersLabel(chapters: number, total: number): string {
    return `${chapters}/${total} chapters`;
}

/** Everyone who has held the subject, oldest first ("Ansari → Bose"). */
export function teacherTrail(subject: CourseSubject): string {
    if (subject.teachers.length === 0) return "No teacher assigned";
    return subject.teachers
        .map((teacher) => (teacher.current ? `${teacher.name} (now)` : teacher.name))
        .join(" → ");
}

export type BadgeTone = "green" | "amber" | "red" | "muted";

/**
 * The ahead/behind badge.
 *
 * * **No plan** - the school never set planned dates; that is not "on time".
 * * **N behind plan** - chapters whose planned date has passed and are not finished.
 * * **On plan** - a plan exists and nothing is late.
 * * **+N early** - some chapters were finished on or before their planned date *and*
 *   nothing is late (so a subject cannot claim both).
 */
export function scheduleBadge(subject: CourseSubject): { label: string; tone: BadgeTone } {
    if (!subject.planned) return { label: "No plan", tone: "muted" };
    if (subject.behind > 0) {
        return {
            label: `${subject.behind} behind plan`,
            tone: subject.behind > 2 ? "red" : "amber",
        };
    }
    const early = subject.chapters.filter((chapter) => chapter.ahead).length;
    if (early > 0) return { label: `+${early} on plan`, tone: "green" };
    return { label: "On plan", tone: "green" };
}

export type TickGate = { allowed: true; reason: null } | { allowed: false; reason: string };

/**
 * May this caller move this chapter, and if not, why?
 *
 * The server answers per chapter (`canTick`); this turns "no" into a sentence the button
 * can carry in its tooltip, so a disabled control still explains itself.
 */
export function tickGate(chapter: CourseChapter): TickGate {
    if (chapter.canTick) return { allowed: true, reason: null };
    return {
        allowed: false,
        reason: "Only the subject's teacher (or the office) can tick this chapter.",
    };
}

/** The status a click on the stepper should send. */
export function nextStatus(chapter: CourseChapter): CourseChapter["status"] {
    return chapter.status === "Completed" ? "Pending" : "Completed";
}

/** The label of the action a caller sees ("Mark done" / "Undo"). */
export function tickLabel(chapter: CourseChapter): string {
    return chapter.status === "Completed" ? "Undo" : "Mark done";
}

function round1(value: number): number {
    return Math.round(value * 10) / 10;
}
