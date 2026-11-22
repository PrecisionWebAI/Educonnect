import assert from "node:assert/strict";
import test from "node:test";

import {
    barSegments,
    canWriteCourse,
    chapterTotals,
    chaptersLabel,
    completionDetail,
    completionWidth,
    historyLabel,
    lessonPlanLabel,
    nextStatus,
    progressText,
    progressWidth,
    reorderSequence,
    scheduleBadge,
    statusBadge,
    teacherName,
    teacherTrail,
    tickGate,
    tickLabel,
} from "./view.ts";
import type { CourseChapter, CourseSubject, CourseTeacher, SectionCourse } from "@/types";

test("course writes need a current academic year", () => {
    assert.equal(canWriteCourse(null), false);
    assert.equal(
        canWriteCourse({
            id: "y1",
            name: "2026-27",
            startDate: "2026-04-01",
            endDate: "2027-03-31",
            isCurrent: true,
        }),
        true,
    );
});

function teacher(partial: Partial<CourseTeacher>): CourseTeacher {
    return {
        employeeId: "e1",
        name: "ansari",
        effectiveFrom: "2026-06-01",
        effectiveTo: null,
        current: true,
        completed: 0,
        ...partial,
    };
}

function chapter(partial: Partial<CourseChapter>): CourseChapter {
    return {
        chapterId: "c1",
        sequence: 1,
        name: "Chapter 1",
        plannedDate: null,
        status: "Pending",
        completedOn: null,
        completedBy: null,
        completedByEmployeeId: null,
        ahead: null,
        behind: false,
        canTick: false,
        canEdit: false,
        ...partial,
    };
}

function subject(partial: Partial<CourseSubject>): CourseSubject {
    return {
        classroomSubjectId: "cs1",
        name: "Mathematics",
        code: null,
        status: "Active",
        currentTeacher: "bose",
        currentTeacherId: "e2",
        teachers: [],
        done: 0,
        total: 10,
        percent: 0,
        nextChapter: "Ch 1 · Chapter 1",
        behind: 0,
        planned: true,
        chapters: [],
        lessonPlan: null,
        canManage: false,
        canAssignTeacher: false,
        canArchive: false,
        canRestore: false,
        canDelete: false,
        ...partial,
    };
}

test("bar: one slice per teacher who finished something, then the remainder", () => {
    // The teacher-change case: 2 of 10 done by the one who left, 0 by the one who came.
    const segments = barSegments(
        subject({
            teachers: [
                teacher({ employeeId: "e1", name: "ansari", completed: 2, current: false }),
                teacher({ employeeId: "e2", name: "bose", completed: 0 }),
            ],
        }),
    );

    assert.deepEqual(
        segments.map((segment) => [segment.label, segment.chapters, segment.share]),
        [
            ["ansari", 2, 20],
            ["Not done", 8, 80],
        ],
        "the 0-chapter teacher gets no slice, the gap is the remainder",
    );
    assert.equal(segments[1].tone, "slate");

    // Shares always add up to the whole plan.
    const total = segments.reduce((sum, segment) => sum + segment.share, 0);
    assert.equal(Math.round(total * 10) / 10, 100);
});

test("bar: a finished plan has no remainder", () => {
    const segments = barSegments(
        subject({
            done: 10,
            percent: 100,
            teachers: [teacher({ completed: 10 })],
        }),
    );
    assert.equal(segments.length, 1);
    assert.equal(segments[0].share, 100);
});

test("bar: no plan draws nothing (the row says so instead)", () => {
    assert.deepEqual(barSegments(subject({ total: 0, percent: null, planned: false })), []);
});

test("badge: no plan, behind plan, on plan - never a green lie", () => {
    assert.deepEqual(scheduleBadge(subject({ planned: false })), {
        label: "No plan",
        tone: "muted",
    });
    assert.deepEqual(scheduleBadge(subject({ behind: 3 })), {
        label: "3 behind plan",
        tone: "red",
    });
    assert.deepEqual(scheduleBadge(subject({ behind: 1 })), {
        label: "1 behind plan",
        tone: "amber",
    });
    assert.deepEqual(
        scheduleBadge(subject({ chapters: [chapter({ ahead: true }), chapter({ ahead: true })] })),
        { label: "+2 on plan", tone: "green" },
    );
    assert.deepEqual(scheduleBadge(subject({})), { label: "On plan", tone: "green" });
});

test("gate: the server's canTick decides, and the refusal explains itself", () => {
    const refused = tickGate(chapter({ canTick: false }));
    assert.equal(refused.allowed, false);
    assert.match(String(refused.reason), /subject's teacher/);

    const allowed = tickGate(chapter({ canTick: true }));
    assert.deepEqual(allowed, { allowed: true, reason: null });
});

test("stepper: a click closes or re-opens, and the label matches", () => {
    const pending = chapter({ status: "Pending" });
    assert.equal(nextStatus(pending), "Completed");
    assert.equal(tickLabel(pending), "Mark done");

    const done = chapter({ status: "Completed" });
    assert.equal(nextStatus(done), "Pending");
    assert.equal(tickLabel(done), "Undo");
});

test("labels: the trail names the current teacher, the count reads n/total", () => {
    assert.equal(
        teacherTrail(
            subject({
                teachers: [
                    teacher({ name: "ansari", current: false }),
                    teacher({ employeeId: "e2", name: "bose", current: true }),
                ],
            }),
        ),
        "ansari → bose (now)",
    );
    assert.equal(teacherTrail(subject({ teachers: [] })), "No teacher assigned");
    assert.equal(chaptersLabel(2, 10), "2/10 chapters");
});

function course(partial: Partial<SectionCourse>): SectionCourse {
    return {
        sectionId: "room1",
        label: "Class 9-A",
        academicYear: "2026-27",
        completionPercent: 60,
        completionSubjects: 2,
        subjectsCount: 2,
        subjects: [],
        ...partial,
    };
}

test("lesson plan cell: this month's weeks, and no plan is not 0 weeks approved", () => {
    assert.equal(lessonPlanLabel(subject({})), "No plan");
    assert.equal(
        lessonPlanLabel(
            subject({
                lessonPlan: {
                    year: 2026,
                    month: 11,
                    submitted: 3,
                    approved: 2,
                    pending: 1,
                    rejected: 0,
                },
            }),
        ),
        "3 submitted · 2 approved",
    );
    assert.equal(
        lessonPlanLabel(
            subject({
                lessonPlan: {
                    year: 2026,
                    month: 11,
                    submitted: 2,
                    approved: 0,
                    pending: 0,
                    rejected: 2,
                },
            }),
        ),
        "2 submitted · 2 rejected",
    );
});

test("history label: a closed row prints its last day, the open one prints now", () => {
    assert.equal(
        historyLabel(
            teacher({ effectiveFrom: "2026-07-01", current: false, effectiveTo: "2026-09-30" }),
        ),
        "01 Jul 2026 → 30 Sep 2026",
    );
    assert.equal(
        historyLabel(teacher({ effectiveFrom: "2026-10-01", current: true })),
        "01 Oct 2026 → now",
    );
});

test("completion card: no subjects, no chapters and a real plan are three states", () => {
    assert.equal(
        completionDetail(course({ subjectsCount: 0, completionPercent: null })),
        "No subjects yet",
    );
    assert.equal(completionDetail(course({ completionPercent: null })), "No chapters planned yet");
    assert.equal(completionDetail(course({})), "2 of 2 subjects have a chapter plan");
    assert.equal(completionWidth(course({ completionPercent: 60 })), "60%");
    assert.equal(completionWidth(course({ completionPercent: null })), "0%");
});

test("reorder: a move is a position, and the edges refuse", () => {
    const rows = [
        chapter({ chapterId: "c1", sequence: 1 }),
        chapter({ chapterId: "c2", sequence: 2 }),
        chapter({ chapterId: "c3", sequence: 3 }),
    ];
    assert.equal(reorderSequence(rows, "c1", "up"), null);
    assert.equal(reorderSequence(rows, "c3", "down"), null);
    assert.equal(reorderSequence(rows, "c3", "up"), 2);
    assert.equal(reorderSequence(rows, "c1", "down"), 2);
    assert.equal(reorderSequence(rows, "missing", "up"), null);
});

test("chapter totals come from the rows, not a stored counter", () => {
    assert.deepEqual(chapterTotals([]), { done: 0, total: 0, percent: null });
    const rows = [
        chapter({ chapterId: "c1", status: "Completed" }),
        chapter({ chapterId: "c2", status: "Pending" }),
        chapter({ chapterId: "c3", status: "Completed" }),
    ];
    assert.deepEqual(chapterTotals(rows), { done: 2, total: 3, percent: 66.7 });
});

test("table words: teacher, progress and state - no plan is not 0%", () => {
    assert.equal(teacherName(subject({})), "bose");
    assert.equal(teacherName(subject({ currentTeacher: null })), "Not assigned");

    assert.equal(progressWidth(subject({ percent: 42.5 })), "42.5%");
    assert.equal(progressWidth(subject({ percent: null })), "0%", "no plan draws no bar");
    assert.equal(progressWidth(subject({ percent: 140 })), "100%", "never overflows");

    assert.equal(progressText(subject({ percent: null })), "No plan");
    assert.equal(progressText(subject({ percent: 100 })), "100%");

    assert.deepEqual(statusBadge(subject({})), { label: "Active", tone: "green" });
    assert.deepEqual(statusBadge(subject({ status: "Archived" })), {
        label: "Archived",
        tone: "muted",
    });
});
