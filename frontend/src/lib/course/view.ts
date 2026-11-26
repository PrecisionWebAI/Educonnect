import type {
    AcademicYear,
    BellSlot,
    CourseChapter,
    CourseSubject,
    CourseTeacher,
    CourseTeacherRow,
    SectionCourse,
} from "@/types";

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

/** Course writes need a current academic year; the server keeps the final `409`. */
export function canWriteCourse(current: AcademicYear | null): boolean {
    return current !== null;
}

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

/** The teacher cell: the person holding the subject today, or the honest blank. */
export function teacherName(subject: CourseSubject): string {
    return subject.currentTeacher ?? "Not assigned";
}

/** The row's percentage as a bar width (`0%` - `100%`). No plan draws an empty bar. */
export function progressWidth(subject: CourseSubject): string {
    const value = subject.percent ?? 0;
    return `${Math.max(0, Math.min(100, value))}%`;
}

/** The percentage word: "No plan" is not the same as "0%". */
export function progressText(subject: CourseSubject): string {
    return subject.percent === null ? "No plan" : `${subject.percent}%`;
}

export type ChapterMove = "up" | "down";

/**
 * The 1-based sequence a move should send, or `null` when the row is already at the edge.
 *
 * The server treats `sequence` as a position and renumbers the whole list, so moving up
 * from position 3 sends 2 and moving down from 2 sends 3 - no swapping in the browser.
 */
export function reorderSequence(
    chapters: CourseChapter[],
    chapterId: string,
    direction: ChapterMove,
): number | null {
    const ordered = [...chapters].sort((left, right) => left.sequence - right.sequence);
    const index = ordered.findIndex((chapter) => chapter.chapterId === chapterId);
    if (index < 0) return null;
    if (direction === "up") return index === 0 ? null : index;
    return index === ordered.length - 1 ? null : index + 2;
}

/**
 * The table's totals, computed from the **real chapter rows** only.
 *
 * No stored counter: adding a chapter changes `total`, a tick changes `done`, and the same
 * two numbers feed the row's bar and the section card.
 */
export function chapterTotals(chapters: CourseChapter[]): {
    done: number;
    total: number;
    percent: number | null;
} {
    const total = chapters.length;
    const done = chapters.filter((chapter) => chapter.status === "Completed").length;
    return {
        done,
        total,
        percent: total === 0 ? null : round1((done / total) * 100),
    };
}

/** The row's state badge: an archived subject is muted, an active one is running. */
export function statusBadge(subject: CourseSubject): {
    label: string;
    tone: BadgeTone;
} {
    return subject.status === "Archived"
        ? { label: "Archived", tone: "muted" }
        : { label: "Active", tone: "green" };
}

/** Everyone who has held the subject, oldest first ("Ansari → Bose"). */
export function teacherTrail(subject: CourseSubject): string {
    if (subject.teachers.length === 0) return "No teacher assigned";
    return subject.teachers
        .map((teacher) => (teacher.current ? `${teacher.name} (now)` : teacher.name))
        .join(" → ");
}

/**
 * The Lesson Plan cell: this month's weeks, or "No plan".
 *
 * `submitted` counts every week with a row, so it includes approved and rejected ones -
 * "3 submitted · 2 approved" is the sentence the row promised, not "1 pending".
 */
export function lessonPlanLabel(subject: CourseSubject): string {
    const plan = subject.lessonPlan;
    if (!plan || plan.submitted === 0) return "No plan";
    const parts = [`${plan.submitted} submitted`];
    if (plan.approved > 0) parts.push(`${plan.approved} approved`);
    else if (plan.pending > 0) parts.push(`${plan.pending} pending`);
    else if (plan.rejected > 0) parts.push(`${plan.rejected} rejected`);
    return parts.join(" · ");
}

/** `01 Jul 2026 → now` - one line of a teacher's assignment. */
export function historyLabel(teacher: CourseTeacher): string {
    return `${shortDate(teacher.effectiveFrom)} → ${
        teacher.current ? "now" : shortDate(teacher.effectiveTo)
    }`;
}

/**
 * The top card's second line. A section with no subjects, a section whose subjects have
 * no chapters and a section with a plan are three different states; 0% is none of them.
 */
export function completionDetail(course: SectionCourse): string {
    if (course.subjectsCount === 0) return "No subjects yet";
    if (course.completionPercent === null) return "No chapters planned yet";
    return `${course.completionSubjects} of ${course.subjectsCount} subject${
        course.subjectsCount === 1 ? "" : "s"
    } have a chapter plan`;
}

/** The top card's bar width (0% - 100%, empty when there is no plan). */
export function completionWidth(course: SectionCourse): string {
    const value = course.completionPercent ?? 0;
    return `${Math.max(0, Math.min(100, value))}%`;
}

function shortDate(value: string | null): string {
    if (!value) return "—";
    const [year, month, day] = value.split("-");
    if (!year || !month || !day) return value;
    const months = [
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
    return `${day} ${months[Number(month) - 1] ?? month} ${year}`;
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

/** The two slices of the utilisation bar and the figure printed beside it. */
export interface UtilisationShares {
    /** Share of the bar (0-100) filled by the teacher's own assigned classes. */
    classes: number;
    /** Share filled by covers for absent colleagues, drawn in its own colour. */
    substitutions: number;
    /** Both together, capped at 100: a bar cannot overflow its track. */
    total: number;
}

/**
 * How much of the session's lesson slots a teacher has filled, split into their own
 * classes and the substitutions they covered.
 *
 * `capacity` is every lesson slot of every open day so far, so the bar answers "of all
 * the classes this teacher could have been in, how many were they in". No capacity (no
 * session or no timetable yet) is an empty bar, never a division by zero. The two slices
 * never add past the track: when they would, the substitution slice is trimmed.
 */
export function utilisationShares(
    classes: number,
    substitutions: number,
    capacity: number,
): UtilisationShares {
    if (capacity <= 0) return { classes: 0, substitutions: 0, total: 0 };
    const own = Math.min(100, Math.max(0, Math.round((classes / capacity) * 100)));
    const cover = Math.min(
        100 - own,
        Math.max(0, Math.round((substitutions / capacity) * 100)),
    );
    return { classes: own, substitutions: cover, total: own + cover };
}

/**
 * Every teaching period of a full school week: the day's regular lessons x the days the
 * school runs (7 less its weekly offs). Breaks and extra classes (E1, E2...) are not
 * periods. Eight lessons over Monday to Saturday is 48.
 */
export function weekCapacity(bell: BellSlot[], weeklyOffDays: number): number {
    const lessons = bell.filter((slot) => !slot.isBreak && !slot.extra).length;
    return lessons * Math.max(7 - weeklyOffDays, 0);
}

/** A teacher's periods as a whole-number percent of the week; 0 when either side is 0. */
export function loadShare(periods: number, capacity: number): number {
    if (capacity <= 0 || periods <= 0) return 0;
    return Math.round((periods * 100) / capacity);
}

export type LoadBand = "Overloaded" | "Steady" | "Light" | "Unassigned";

/** The Load bands: under 60% Light, over 100% Overloaded, Steady between. */
export function loadBandOf(percent: number, capacity: number): LoadBand {
    if (capacity <= 0) return "Unassigned";
    if (percent > 100) return "Overloaded";
    if (percent < 60) return "Light";
    return "Steady";
}

// ---- Teachers > Course: the filter and the sort ------------------------------------

/** What the filter's first dropdown can pick. */
export type TeacherFilterField = "teacher" | "department" | "classCov" | "subjectCov";

export interface TeacherFilter {
    field: TeacherFilterField;
    /** The option chosen in the second dropdown. */
    value: string;
}

export interface FilterOption {
    value: string;
    label: string;
}

/**
 * Subject names as they are always shown and compared: trimmed, lowercase, once each, A-Z.
 * "Maths", "maths " and "MATHS" are one subject, written "maths" - the names are typed by
 * hand per class-section, so the same subject arrives in many spellings.
 */
export function uniqueSubjects(names: readonly string[] | null | undefined): string[] {
    const seen = new Set<string>();
    for (const raw of names ?? []) {
        const name = raw.trim().toLowerCase();
        if (name) seen.add(name);
    }
    return [...seen].sort((a, b) => a.localeCompare(b));
}

const byLabel = (a: FilterOption, b: FilterOption) =>
    a.label.localeCompare(b.label, undefined, { sensitivity: "base", numeric: true });

/**
 * The second dropdown's choices for a field, built from the rows themselves so it only
 * offers what exists: teachers and departments and subjects A to Z, class-sections in school
 * order (the class's `level`, then the section letter - "Class 2" before "Class 10").
 */
export function filterOptions(
    rows: CourseTeacherRow[],
    field: TeacherFilterField,
): FilterOption[] {
    if (field === "teacher") {
        return rows
            .map((row) => ({ value: row.employeeId, label: row.name }))
            .sort(byLabel);
    }
    if (field === "department") {
        // Once each however it was typed: "Science", "science " and "SCIENCE" are one
        // department, listed under the first spelling seen.
        const seen = new Map<string, string>();
        for (const row of rows) {
            const name = (row.department ?? "").trim();
            if (name && !seen.has(name.toLowerCase())) seen.set(name.toLowerCase(), name);
        }
        return [...seen.values()].map((name) => ({ value: name, label: name })).sort(byLabel);
    }
    if (field === "subjectCov") {
        return uniqueSubjects(rows.flatMap((row) => row.subjects ?? [])).map((name) => ({
            value: name,
            label: name,
        }));
    }
    const sections = new Map<string, { level: number; option: FilterOption }>();
    for (const row of rows)
        for (const item of row.classes ?? [])
            for (const section of item.sections)
                sections.set(`${item.className}|${section}`, {
                    level: item.level ?? 0,
                    option: {
                        value: `${item.className}|${section}`,
                        label: `${item.className} ${section}`,
                    },
                });
    return [...sections.values()]
        .sort((a, b) => a.level - b.level || byLabel(a.option, b.option))
        .map((entry) => entry.option);
}

/** True when a teacher passes the filter; no filter (or no value yet) passes everyone. */
export function matchesFilter(row: CourseTeacherRow, filter: TeacherFilter | null): boolean {
    if (!filter || !filter.value) return true;
    switch (filter.field) {
        case "teacher":
            return row.employeeId === filter.value;
        case "department":
            return (
                (row.department ?? "").trim().toLowerCase() === filter.value.trim().toLowerCase()
            );
        case "subjectCov":
            return uniqueSubjects(row.subjects).includes(filter.value.trim().toLowerCase());
        case "classCov": {
            // Teaching that section is enough; teaching its sister sections too is fine.
            const [className, section] = filter.value.split("|");
            return (row.classes ?? []).some(
                (item) => item.className === className && item.sections.includes(section),
            );
        }
    }
}

/** What the Sort by dropdown can order by. */
export type TeacherSortKey =
    | "chapters"
    | "periods"
    | "load"
    | "classes"
    | "substitution"
    | "utilisation";

export type SortDirection = "asc" | "desc";

/**
 * A sorted copy. Equal values keep the teachers' A-Z order, so the list never jumps around
 * between two teachers who tie. `loadOf` is the Load/wk figure the table prints, passed in
 * because it can be worked out in the browser when the server does not send it.
 */
export function sortTeachers(
    rows: CourseTeacherRow[],
    key: TeacherSortKey | "",
    direction: SortDirection,
    loadOf: (row: CourseTeacherRow) => number,
): CourseTeacherRow[] {
    const byName = (a: CourseTeacherRow, b: CourseTeacherRow) =>
        a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
    if (!key) return [...rows].sort(byName);
    const value = (row: CourseTeacherRow): number => {
        switch (key) {
            case "chapters":
                return row.chaptersPerMonth ?? 0;
            case "periods":
                return row.periodsPerWeek ?? 0;
            case "load":
                return loadOf(row);
            case "classes":
                return row.classesYearly ?? 0;
            case "substitution":
                return row.substitutionsYearly ?? 0;
            case "utilisation":
                return utilisationShares(
                    row.classesYearly ?? 0,
                    row.substitutionsYearly ?? 0,
                    row.capacityYearly ?? 0,
                ).total;
        }
    };
    const sign = direction === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => sign * (value(a) - value(b)) || byName(a, b));
}
