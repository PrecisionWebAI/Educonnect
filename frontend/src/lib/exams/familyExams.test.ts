import assert from "node:assert/strict";
import test from "node:test";

import {
    familySubtitle,
    familyTitle,
    firstDate,
    hasSyllabusColumn,
    sortForFamily,
} from "./familyExams.ts";
import type { ExamPaperPlan, ExamPlan } from "@/types";

function paper(partial: Partial<ExamPaperPlan> = {}): ExamPaperPlan {
    return {
        id: "p",
        examId: "e",
        classroomSubjectId: "s",
        classroomId: "r",
        classId: "c",
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
        canEdit: false,
        canDetach: false,
        ...partial,
    };
}

function exam(partial: Partial<ExamPlan> = {}): ExamPlan {
    return {
        id: "e",
        name: "Unit Test",
        term: null,
        examType: "unit_test",
        scope: "class",
        status: "scheduled",
        classId: "c",
        classroomId: "r",
        academicYearId: null,
        startDate: null,
        endDate: null,
        note: null,
        familyNote: null,
        datesheetPublishedAt: "2026-11-30T10:00:00",
        archivedAt: null,
        canManage: false,
        publishedAt: null,
        papers: [paper()],
        groups: [],
        skipped: [],
        ...partial,
    };
}

test("the earliest date of an exam is the first day on its date sheet", () => {
    const sheet = exam({
        papers: [paper({ examDate: "2027-01-14" }), paper({ examDate: "2027-01-12" })],
    });
    assert.equal(firstDate(sheet), "2027-01-12");
    assert.equal(firstDate(exam({ papers: [paper({ examDate: null })] })), null);
});

test("the soonest exam comes first, an undated one after, a cancelled one last", () => {
    const later = exam({
        id: "later",
        name: "Annual",
        papers: [paper({ examDate: "2027-03-01" })],
    });
    const sooner = exam({
        id: "sooner",
        name: "Unit",
        papers: [paper({ examDate: "2026-12-05" })],
    });
    const undated = exam({ id: "undated", name: "Quiz", papers: [paper({ examDate: null })] });
    const cancelled = exam({
        id: "cancelled",
        name: "Old",
        status: "cancelled",
        papers: [paper({ examDate: "2026-11-01" })],
    });
    assert.deepEqual(
        sortForFamily([cancelled, undated, later, sooner]).map((item) => item.id),
        ["sooner", "later", "undated", "cancelled"],
    );
});

test("a class test is titled by its subject and dated; a school exam by its name and type", () => {
    const test_ = exam({ examType: "class_test", name: "Class Test - Mathematics" });
    assert.equal(familyTitle(test_), "Class Test · Mathematics");
    assert.equal(familySubtitle(test_), "5 Dec");

    const sheet = exam({ examType: "half_yearly", name: "Half Yearly" });
    assert.equal(familyTitle(sheet), "Half Yearly");
    assert.equal(familySubtitle(sheet), "Half Yearly");
});

test("only a school exam's card has syllabus buttons", () => {
    assert.equal(hasSyllabusColumn(exam()), true);
    assert.equal(hasSyllabusColumn(exam({ examType: "class_test" })), true);
    assert.equal(hasSyllabusColumn(exam({ examType: "Mid term" })), false);
});
