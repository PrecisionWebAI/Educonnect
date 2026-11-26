import assert from "node:assert/strict";
import test from "node:test";

import type { LadderRung } from "./marking.ts";
import {
    changeText,
    figuresFor,
    ladderOf,
    passCounts,
    passesPaper,
    percentCell,
} from "./marksSheet.ts";
import type { MarkEdit } from "./view.ts";
import type { ExamPaperPlan } from "@/types";

const LADDER: LadderRung[] = [
    { minPercent: 90, grade: "A1" },
    { minPercent: 33, grade: "D" },
    { minPercent: 0, grade: "E" },
];

function paper(partial: Partial<ExamPaperPlan> = {}): ExamPaperPlan {
    return {
        id: "p1",
        examId: "e1",
        classroomSubjectId: "s1",
        classroomId: "r1",
        classId: "c1",
        section: "Class 9-A",
        subject: "Mathematics",
        title: "Mathematics",
        paperGroupId: null,
        groupLocked: false,
        examDate: "2026-12-05",
        startTime: null,
        endTime: null,
        maxMarks: "50.00",
        passingMarks: "16.50",
        room: null,
        note: null,
        publishedAt: null,
        chapterIds: [],
        chapters: [],
        marksEntered: 0,
        takenByEmployeeId: null,
        takenByName: null,
        assignedTeacherId: null,
        assignedTeacherName: null,
        isTemporary: false,
        passMode: "marks",
        passPercent: "33.00",
        passingGrade: null,
        gradingScale: [],
        hasSyllabus: false,
        gradeMode: "auto",
        syllabusByEmployeeId: null,
        syllabusByName: null,
        syllabusIsTemporary: false,
        canSyllabus: false,
        canEdit: true,
        canDetach: false,
        ...partial,
    };
}

function edit(score: string, absent = false): MarkEdit {
    return {
        studentId: "st",
        name: "Aarav",
        admissionNumber: "A1",
        section: null,
        score,
        absent,
        saved: null,
    };
}

test("a typed score shows its percentage, grade and result at once", () => {
    const found = figuresFor(edit("45"), paper(), LADDER);
    assert.deepEqual(found, { state: "marked", percentage: 90, grade: "A1", passed: true });
});

test("pass is judged on the pass marks, including the half mark", () => {
    assert.equal(figuresFor(edit("16.5"), paper(), LADDER).passed, true);
    assert.equal(figuresFor(edit("16"), paper(), LADDER).passed, false);
});

test("a grade-based paper passes at the grade's percentage, not at a number of marks", () => {
    const graded = paper({ passMode: "grade", passPercent: "40.00", passingGrade: "C2" });
    assert.equal(passesPaper(20, graded), true);
    assert.equal(passesPaper(19, graded), false);
});

test("zero is a score and a fail; an absence is neither", () => {
    const zero = figuresFor(edit("0"), paper(), LADDER);
    assert.equal(zero.state, "marked");
    assert.equal(zero.percentage, 0);
    assert.equal(zero.passed, false);

    const absent = figuresFor(edit("", true), paper(), LADDER);
    assert.deepEqual(absent, { state: "absent", percentage: null, grade: null, passed: null });
});

test("a blank or impossible score has nothing to show", () => {
    assert.equal(figuresFor(edit(""), paper(), LADDER).state, "blank");
    assert.equal(figuresFor(edit("51"), paper(), LADDER).state, "invalid");
    assert.equal(figuresFor(edit("-1"), paper(), LADDER).state, "invalid");
    assert.equal(figuresFor(edit("abc"), paper(), LADDER).state, "blank");
});

test("the paper's own ladder wins over the school's", () => {
    const own = paper({ gradingScale: [{ minPercent: "0.00", grade: "Z" }] });
    assert.deepEqual(ladderOf(own, LADDER), [{ minPercent: 0, grade: "Z" }]);
    assert.equal(figuresFor(edit("45"), own, ladderOf(own, LADDER)).grade, "Z");
    assert.deepEqual(ladderOf(paper(), LADDER), LADDER, "an older paper uses the school's");
});

test("the counts cover only the children who can be judged", () => {
    const edits = [edit("45"), edit("10"), edit("", true), edit("")];
    assert.deepEqual(passCounts(edits, paper(), LADDER), { passed: 1, failed: 1 });
});

test("a percentage reads without trailing zeros, and a missing one as a dash", () => {
    assert.equal(percentCell(90), "90%");
    assert.equal(percentCell(33.33), "33.33%");
    assert.equal(percentCell(null), "—");
});

test("a correction reads as old to new, an absence as a word", () => {
    assert.equal(
        changeText({ oldValue: "45.00", newValue: "10.00", oldAbsent: false, newAbsent: false }),
        "45 → 10",
    );
    assert.equal(
        changeText({ oldValue: "45.00", newValue: null, oldAbsent: false, newAbsent: true }),
        "45 → Absent",
    );
    assert.equal(
        changeText({ oldValue: null, newValue: "30.50", oldAbsent: true, newAbsent: false }),
        "Absent → 30.5",
    );
});
