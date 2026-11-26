import assert from "node:assert/strict";
import test from "node:test";

import { editPassMarks, type LadderRung } from "./marking.ts";
import {
    SCHOOL_EXAM_TYPES,
    blankSchoolExamDraft,
    isSchoolExamType,
    passText,
    schoolExamChip,
    schoolExamCreateBody,
    schoolExamDraftFromExam,
    schoolExamProblems,
    schoolExamUpdateBody,
    splitSchoolByDate,
    syllabusProgress,
    typeLabel,
} from "./schoolExam.ts";
import type { ExamPaperPlan, ExamPlan } from "@/types";

const SUBJECTS = [
    { id: "s1", name: "Mathematics" },
    { id: "s2", name: "Science" },
];
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
        examDate: "2027-01-12",
        startTime: null,
        endTime: null,
        maxMarks: "100.00",
        passingMarks: "33.00",
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
        canSyllabus: true,
        canEdit: true,
        canDetach: false,
        ...partial,
    };
}

function exam(partial: Partial<ExamPlan> = {}): ExamPlan {
    return {
        id: "e1",
        name: "Unit Test",
        term: null,
        examType: "unit_test",
        scope: "class",
        status: "draft",
        classId: "c1",
        classroomId: "r1",
        academicYearId: null,
        startDate: null,
        endDate: null,
        note: null,
        familyNote: "Reach early",
        datesheetPublishedAt: null,
        archivedAt: null,
        canManage: true,
        publishedAt: null,
        papers: [paper()],
        groups: [],
        skipped: [],
        ...partial,
    };
}

function filled() {
    const draft = blankSchoolExamDraft(SUBJECTS);
    draft.examType = "unit_test";
    draft.rows[0].examDate = "2027-01-12";
    draft.rows[1].examDate = "2027-01-14";
    return draft;
}

test("the types are the spec's list, in order, and only they count as school exam types", () => {
    assert.deepEqual(
        SCHOOL_EXAM_TYPES.map((item) => item.label),
        [
            "Unit Test",
            "Periodic Test",
            "Mid Term Test",
            "Half Yearly",
            "Annual",
            "Pre-Board",
            "Practical",
            "Custom",
        ],
    );
    assert.equal(isSchoolExamType("half_yearly"), true);
    assert.equal(isSchoolExamType("class_test"), false);
    assert.equal(isSchoolExamType("Mid term"), false, "an older free-text type is not one");
    assert.equal(isSchoolExamType(null), false);
    assert.equal(typeLabel("pre_board"), "Pre-Board");
});

test("a new date sheet lists every subject, switched on, at 33% of a full paper", () => {
    const draft = blankSchoolExamDraft(SUBJECTS);
    assert.equal(draft.rows.length, 2);
    assert.ok(draft.rows.every((row) => row.included && row.total === "100"));
    assert.equal(draft.rows[0].passLine.passMarks, "33");
});

test("the form says what is missing, naming the subject", () => {
    const empty = blankSchoolExamDraft(SUBJECTS);
    assert.deepEqual(schoolExamProblems(empty, LADDER).slice(0, 3), [
        "Choose the type of exam.",
        "Mathematics: choose the date.",
        "Science: choose the date.",
    ]);
    assert.deepEqual(schoolExamProblems(filled(), LADDER), []);
});

test("custom needs a name and the sheet needs a subject", () => {
    const custom = { ...filled(), examType: "custom" };
    assert.deepEqual(schoolExamProblems(custom, LADDER), ["Type the name of this exam."]);
    const none = filled();
    none.rows.forEach((row) => (row.included = false));
    assert.deepEqual(schoolExamProblems(none, LADDER), [
        "Keep at least one subject on the date sheet.",
    ]);
});

test("a pass line that cannot be true names its subject", () => {
    const draft = filled();
    draft.rows[1].passLine = editPassMarks(draft.rows[1].passLine, "500");
    assert.match(schoolExamProblems(draft, LADDER)[0], /^Science: Passing marks cannot be more/);
});

test("the create body carries only the subjects that are switched on, each with its pass line", () => {
    const draft = filled();
    draft.familyNote = "  Reach early  ";
    draft.rows[1].included = false;
    assert.deepEqual(schoolExamCreateBody(draft, "r1"), {
        classroom_id: "r1",
        confirm_duplicate: false,
        exam_type: "unit_test",
        custom_name: null,
        family_note: "Reach early",
        rows: [
            {
                classroom_subject_id: "s1",
                exam_date: "2027-01-12",
                total_marks: 100,
                taken_by_employee_id: null,
                pass_mode: "marks",
                passing_marks: 33,
                passing_grade: null,
                custom_min_percent: null,
                grade_mode: "na",
            },
        ],
    });
    const custom = { ...filled(), examType: "custom", customName: " Science Fair " };
    assert.equal(schoolExamCreateBody(custom, "r1").custom_name, "Science Fair");
});

test("editing opens with what is saved; a subject not on the sheet starts switched off", () => {
    const draft = schoolExamDraftFromExam(exam(), SUBJECTS);
    assert.equal(draft.examType, "unit_test");
    assert.equal(draft.familyNote, "Reach early");
    assert.equal(draft.rows[0].included, true);
    assert.equal(draft.rows[0].examDate, "2027-01-12");
    assert.equal(draft.rows[0].passLine.passMarksEdited, false, "33 is the default");
    assert.equal(draft.rows[1].included, false);

    const own = schoolExamDraftFromExam(
        exam({ papers: [paper({ passingMarks: "40.00" })] }),
        SUBJECTS,
    );
    assert.equal(own.rows[0].passLine.passMarksEdited, true);

    const custom = schoolExamDraftFromExam(
        exam({ examType: "custom", name: "Science Fair" }),
        SUBJECTS,
    );
    assert.equal(custom.customName, "Science Fair");
});

test("the update body sends the sheet, and the type or note only when they changed", () => {
    const original = exam();
    const same = schoolExamDraftFromExam(original, SUBJECTS);
    const unchanged = schoolExamUpdateBody(same, original);
    assert.deepEqual(Object.keys(unchanged), ["rows"]);

    const changed = schoolExamUpdateBody(
        { ...same, examType: "annual", familyNote: "Bring a pen" },
        original,
    );
    assert.equal(changed.exam_type, "annual");
    assert.equal(changed.custom_name, null);
    assert.equal(changed.family_note, "Bring a pen");
});

test("the chip is Draft until published, then Published, and Cancelled when called off", () => {
    assert.deepEqual(schoolExamChip(exam()), { label: "Draft", tone: "muted" });
    assert.deepEqual(schoolExamChip(exam({ datesheetPublishedAt: "2027-01-01T10:00:00" })), {
        label: "Published",
        tone: "green",
    });
    assert.deepEqual(schoolExamChip(exam({ status: "cancelled" })), {
        label: "Cancelled",
        tone: "red",
    });
});

test("a pass line reads as marks with its percent, or as a grade", () => {
    assert.equal(passText(paper()), "33 (33%)");
    assert.equal(passText(paper({ passingMarks: "40.00", passPercent: "40.00" })), "40 (40%)");
    assert.equal(passText(paper({ passMode: "grade", passingGrade: "D" })), "Grade D");
    assert.equal(passText(paper({ passingMarks: null })), "—");
});

test("syllabus progress counts the subjects that have one written", () => {
    const sheet = exam({
        papers: [paper({ hasSyllabus: true }), paper({ id: "p2", hasSyllabus: false })],
    });
    assert.deepEqual(syllabusProgress(sheet), { written: 1, total: 2 });
});

test("school exams split by the last day on the date sheet: upcoming nearest first, past latest first", () => {
    const sheet = (id: string, days: (string | null)[]) =>
        ({
            id,
            endDate: null,
            startDate: null,
            papers: days.map((examDate) => ({ examDate })),
        }) as unknown as ExamPlan;
    const { upcoming, past } = splitSchoolByDate(
        [
            sheet("ends-late", ["2026-12-01", "2026-12-20"]),
            sheet("over", ["2026-11-01", "2026-11-05"]),
            sheet("ends-today", ["2026-12-05"]),
            sheet("recent", ["2026-12-01"]),
            sheet("undated", [null]),
        ],
        "2026-12-05",
    );
    assert.deepEqual(
        upcoming.map((item) => item.id),
        ["ends-today", "ends-late", "undated"],
    );
    assert.deepEqual(
        past.map((item) => item.id),
        ["recent", "over"],
    );
});

test("a subject's Taken By goes in the body, a temporary teacher reopens as one, and 'create anyway' is sent", () => {
    const draft = filled();
    draft.rows[0].takenBy = "t9";
    const body = schoolExamCreateBody(draft, "r1", { confirmDuplicate: true });
    assert.equal(body.confirm_duplicate, true);
    assert.equal(
        (body.rows as { taken_by_employee_id: string | null }[])[0].taken_by_employee_id,
        "t9",
    );
    assert.equal(
        (schoolExamUpdateBody(draft, exam(), { confirmDuplicate: true }) as Record<string, unknown>)
            .confirm_duplicate,
        true,
    );
    const temp = schoolExamDraftFromExam(
        exam({ papers: [paper({ isTemporary: true, takenByEmployeeId: "t9" })] }),
        SUBJECTS,
    );
    assert.equal(temp.rows[0].takenBy, "t9");
    const assigned = schoolExamDraftFromExam(
        exam({ papers: [paper({ isTemporary: false, takenByEmployeeId: "t1" })] }),
        SUBJECTS,
    );
    assert.equal(assigned.rows[0].takenBy, "", "the assigned teacher is not a choice");
});
