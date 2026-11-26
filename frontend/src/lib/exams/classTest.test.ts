import assert from "node:assert/strict";
import test from "node:test";

import {
    splitByDate,
    todayText,
    blankClassTestDraft,
    classTestChip,
    classTestCreateBody,
    classTestDraftFromExam,
    classTestPatch,
    classTestProblems,
    duplicatesFrom,
    hasMarks,
    sectionsText,
    type ClassTestDraft,
} from "./classTest.ts";
import { editPassMarks, type LadderRung } from "./marking.ts";
import type { ExamPaperPlan, ExamPlan } from "@/types";

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
        takenByEmployeeId: "t1",
        takenByName: "Meera",
        assignedTeacherId: "t1",
        assignedTeacherName: "Meera",
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

function exam(partial: Partial<ExamPlan> = {}): ExamPlan {
    return {
        id: "e1",
        name: "Class Test - Mathematics",
        term: null,
        examType: "class_test",
        scope: "class",
        status: "scheduled",
        classId: "c1",
        classroomId: null,
        academicYearId: null,
        startDate: null,
        endDate: null,
        note: null,
        familyNote: "Bring a ruler",
        datesheetPublishedAt: null,
        archivedAt: null,
        canManage: false,
        publishedAt: null,
        papers: [paper()],
        groups: [],
        skipped: [],
        ...partial,
    };
}

function filled(partial: Partial<ClassTestDraft> = {}): ClassTestDraft {
    return {
        ...blankClassTestDraft({ classroomId: "r1", subjectId: "s1" }),
        examDate: "2026-12-05",
        total: "50",
        passLine: editPassMarks(blankClassTestDraft({ classroomId: "r1" }).passLine, "16.5"),
        ...partial,
    };
}

test("a new test starts on the section it was opened from", () => {
    const draft = blankClassTestDraft({ classroomId: "r1", subjectId: "s1" });
    assert.deepEqual(draft.sectionIds, ["r1"]);
    assert.equal(draft.takenBy, "", "the assigned teacher is the default");
    assert.equal(draft.examDate, "");
});

test("the form says what is missing before the server has to", () => {
    const empty = blankClassTestDraft({ classroomId: "r1" });
    const found = classTestProblems({ ...empty, sectionIds: [] }, LADDER);
    assert.deepEqual(found.slice(0, 4), [
        "Choose the subject.",
        "Choose at least one section.",
        "Choose the date of the test.",
        "Enter the total marks.",
    ]);
    assert.deepEqual(classTestProblems(filled(), LADDER), []);
});

test("a section with nobody assigned needs a teacher picked", () => {
    assert.deepEqual(classTestProblems(filled(), LADDER, { needsTaker: true }), [
        "Pick who takes the test.",
    ]);
    assert.deepEqual(
        classTestProblems(filled({ takenBy: "t9" }), LADDER, { needsTaker: true }),
        [],
    );
});

test("a pass line that cannot be true keeps the test from saving", () => {
    const tooHigh = filled({
        passLine: editPassMarks(filled().passLine, "60"),
    });
    assert.match(classTestProblems(tooHigh, LADDER)[0], /more than the total/);
});

test("the create body carries the section list, the pass line and the duplicate flag", () => {
    const body = classTestCreateBody(
        filled({ sectionIds: ["r1", "r2"], takenBy: "t9", familyNote: "  Bring a ruler  " }),
        { confirmDuplicate: true },
    );
    assert.deepEqual(body, {
        classroom_subject_id: "s1",
        section_ids: ["r1", "r2"],
        exam_date: "2026-12-05",
        total_marks: 50,
        taken_by_employee_id: "t9",
        family_note: "Bring a ruler",
        syllabus_text: null,
        pass_mode: "marks",
        passing_marks: 16.5,
        passing_grade: null,
        custom_min_percent: null,
        grade_mode: "na",
        confirm_duplicate: true,
    });
    assert.equal(classTestCreateBody(filled()).taken_by_employee_id, null);
    assert.equal(classTestCreateBody(filled({ familyNote: "  " })).family_note, null);
});

test("the syllabus is free text: sent trimmed, cleared with nothing, and only patched when it changed", () => {
    assert.equal(
        classTestCreateBody(filled({ syllabus: "  Chapter 3 and 4  " })).syllabus_text,
        "Chapter 3 and 4",
    );
    assert.equal(classTestCreateBody(filled({ syllabus: "  " })).syllabus_text, null);
    const saved = classTestDraftFromExam(exam(), "Chapter 3");
    assert.equal(saved.syllabus, "Chapter 3");
    assert.deepEqual(classTestPatch(saved, exam(), { savedSyllabus: "Chapter 3" }), {});
    assert.deepEqual(
        classTestPatch({ ...saved, syllabus: "Chapter 5" }, exam(), { savedSyllabus: "Chapter 3" }),
        { syllabus_text: "Chapter 5" },
    );
    assert.deepEqual(
        classTestPatch({ ...saved, syllabus: "" }, exam(), { savedSyllabus: "Chapter 3" }),
        { syllabus_text: null },
    );
});

test("editing opens with what is saved, and the 33% number keeps following the total", () => {
    const draft = classTestDraftFromExam(exam());
    assert.equal(draft.examDate, "2026-12-05");
    assert.equal(draft.total, "50");
    assert.equal(draft.takenBy, "", "the assigned teacher is not a choice");
    assert.equal(draft.familyNote, "Bring a ruler");
    assert.equal(draft.passLine.passMarks, "16.5");
    assert.equal(draft.passLine.passMarksEdited, false);

    const own = classTestDraftFromExam(exam({ papers: [paper({ passingMarks: "25.00" })] }));
    assert.equal(own.passLine.passMarksEdited, true, "the teacher's own number stays put");
});

test("a temporary teacher is a choice and reopens as one", () => {
    const draft = classTestDraftFromExam(
        exam({
            papers: [paper({ takenByEmployeeId: "t2", takenByName: "Cover", isTemporary: true })],
        }),
    );
    assert.equal(draft.takenBy, "t2");
});

test("the patch carries only what changed - and nothing when nothing did", () => {
    const original = exam();
    const same = classTestDraftFromExam(original);
    assert.deepEqual(classTestPatch(same, original), {});

    assert.deepEqual(classTestPatch({ ...same, examDate: "2026-12-08" }, original), {
        exam_date: "2026-12-08",
    });
    assert.deepEqual(classTestPatch({ ...same, familyNote: "Bring a compass" }, original), {
        family_note: "Bring a compass",
    });
    assert.deepEqual(classTestPatch({ ...same, familyNote: "" }, original), {
        family_note: null,
    });
    assert.deepEqual(classTestPatch({ ...same, sectionIds: ["r1", "r2"] }, original), {
        section_ids: ["r1", "r2"],
    });
    assert.deepEqual(classTestPatch({ ...same, takenBy: "t2" }, original), {
        taken_by_employee_id: "t2",
    });
});

test("a changed total sends the total and the pass line that followed it", () => {
    const original = exam();
    const draft = classTestDraftFromExam(original);
    const patch = classTestPatch(
        { ...draft, total: "40", passLine: { ...draft.passLine, passMarks: "13.2" } },
        original,
    );
    assert.equal(patch.total_marks, 40);
    assert.equal(patch.pass_mode, "marks");
    assert.equal(patch.passing_marks, 13.2);
});

test("the duplicate flag is only added to a patch that sends something", () => {
    const original = exam();
    const draft = classTestDraftFromExam(original);
    assert.deepEqual(classTestPatch(draft, original, { confirmDuplicate: true }), {});
    assert.deepEqual(
        classTestPatch({ ...draft, examDate: "2026-12-08" }, original, { confirmDuplicate: true }),
        { exam_date: "2026-12-08", confirm_duplicate: true },
    );
});

test("the duplicate warning is read from a 409 and from nothing else", () => {
    const error = {
        code: "DUPLICATE_EXAM",
        detail: {
            code: "DUPLICATE_EXAM",
            existing: [
                {
                    exam_id: "e9",
                    name: "Class Test - Mathematics",
                    exam_date: "2026-12-05",
                    subject: "Mathematics",
                    total_marks: "50.00",
                    section: "Class 9-A",
                    created_by: "Meera",
                    status: "scheduled",
                },
            ],
        },
    };
    const found = duplicatesFrom(error);
    assert.equal(found?.length, 1);
    assert.equal(found?.[0].createdBy, "Meera");
    assert.equal(found?.[0].examId, "e9");
    assert.equal(duplicatesFrom({ code: "other" }), null);
    assert.equal(duplicatesFrom(new Error("boom")), null);
    assert.equal(duplicatesFrom(null), null);
});

test("the chip is Scheduled until marks exist, Completed after, Cancelled when called off", () => {
    assert.deepEqual(classTestChip(exam()), { label: "Scheduled", tone: "accent" });
    assert.deepEqual(classTestChip(exam({ papers: [paper({ marksEntered: 3 })] })), {
        label: "Completed",
        tone: "green",
    });
    assert.deepEqual(classTestChip(exam({ status: "cancelled" })), {
        label: "Cancelled",
        tone: "red",
    });
});

test("sections read short, and marks decide whether it can be deleted", () => {
    const two = exam({
        papers: [paper(), paper({ id: "p2", classroomId: "r2", section: "Class 9-B" })],
    });
    assert.equal(sectionsText(two), "9-A, 9-B");
    assert.equal(hasMarks(two), false);
    assert.equal(hasMarks(exam({ papers: [paper({ marksEntered: 1 })] })), true);
});

test("class tests split into upcoming (nearest first) and past (latest first) by their date", () => {
    const on = (id: string, day: string | null) =>
        exam({ id, papers: [paper({ classroomId: "r1", examDate: day })] });
    const exams = [
        on("later", "2026-12-20"),
        on("old", "2026-11-01"),
        on("today", "2026-12-05"),
        on("recent", "2026-12-01"),
        on("undated", null),
        on("soon", "2026-12-08"),
    ];
    const { upcoming, past } = splitByDate(exams, "r1", "2026-12-05");
    assert.deepEqual(
        upcoming.map((item) => item.id),
        ["today", "soon", "later", "undated"],
        "today is still upcoming; nearest first",
    );
    assert.deepEqual(
        past.map((item) => item.id),
        ["recent", "old"],
        "most recent first",
    );
    assert.equal(todayText(new Date(2026, 0, 9)), "2026-01-09");
});

test("the Grade column's mode is part of the form: it goes in the body and is patched when changed", () => {
    const draft = filled({ passLine: { ...filled().passLine, gradeMode: "manual" } });
    assert.equal(classTestCreateBody(draft).grade_mode, "manual");
    const saved = classTestDraftFromExam(exam());
    assert.equal(saved.passLine.gradeMode, "auto", "what the paper holds");
    assert.deepEqual(classTestPatch(saved, exam()), {});
    const patch = classTestPatch(
        { ...saved, passLine: { ...saved.passLine, gradeMode: "manual" } },
        exam(),
    );
    assert.equal(patch.grade_mode, "manual");
});
