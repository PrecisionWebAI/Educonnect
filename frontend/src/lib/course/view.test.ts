import assert from "node:assert/strict";
import test from "node:test";

import {
    barSegments,
    chaptersLabel,
    nextStatus,
    scheduleBadge,
    teacherTrail,
    tickGate,
    tickLabel,
} from "./view.ts";
import type { CourseChapter, CourseSubject, CourseTeacher } from "@/types";

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
        progressId: null,
        ahead: null,
        behind: false,
        canTick: false,
        ...partial,
    };
}

function subject(partial: Partial<CourseSubject>): CourseSubject {
    return {
        subjectId: "s1",
        subject: "Mathematics",
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
