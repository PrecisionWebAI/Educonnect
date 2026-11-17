import assert from "node:assert/strict";
import test from "node:test";

import {
    amount,
    blankDraft,
    blankPaper,
    changedEdits,
    clockText,
    dateRangeText,
    dayText,
    draftBody,
    draftFromExam,
    draftProblems,
    editFromRows,
    examStatusChip,
    figureText,
    forSection,
    gradeTone,
    isBlankPaper,
    markCellText,
    marksEntries,
    paperProgress,
    paperWhenText,
    passText,
    percentText,
    publishGate,
    rankText,
    rowChanged,
    scoreProblem,
    sheetCounts,
    splitByScope,
    unpublishedSubjects,
} from "./view.ts";
import type { ExamPaperPlan, ExamPlan, ExamResults, PaperMarkRow } from "@/types";

function paper(partial: Partial<ExamPaperPlan> = {}): ExamPaperPlan {
    return {
        id: "p1",
        examId: "e1",
        subjectId: "s1",
        subject: "Mathematics",
        classId: "c1",
        examDate: "2026-03-12",
        startTime: "09:00:00",
        endTime: "12:00:00",
        maxMarks: "100.00",
        passingMarks: "33.00",
        room: "4",
        note: null,
        publishedAt: null,
        chapterIds: [],
        chapters: [],
        marksEntered: 0,
        canEdit: true,
        ...partial,
    };
}

function exam(partial: Partial<ExamPlan> = {}): ExamPlan {
    return {
        id: "e1",
        name: "Mid-Term",
        term: "Term 1",
        examType: "Mid-term",
        scope: "class",
        status: "scheduled",
        classId: "c1",
        classroomId: "r1",
        academicYearId: null,
        startDate: "2026-03-12",
        endDate: "2026-03-20",
        note: null,
        publishedAt: null,
        papers: [],
        ...partial,
    };
}

function row(partial: Partial<PaperMarkRow> = {}): PaperMarkRow {
    return {
        studentId: "st1",
        name: "Aarav",
        admissionNumber: "ADM-1",
        section: "A",
        marksObtained: "72.50",
        absent: false,
        grade: null,
        changedAfterPublish: false,
        ...partial,
    };
}

test("decimals: pydantic's strings become numbers, and a blank is not zero", () => {
    assert.equal(amount("72.50"), 72.5);
    assert.equal(amount(72.5), 72.5);
    assert.equal(amount("  "), null);
    assert.equal(amount(null), null);
    assert.equal(amount("abc"), null);

    assert.equal(figureText("72.50"), "72.5");
    assert.equal(figureText("100.00"), "100");
    assert.equal(figureText(null), "—");
    assert.equal(percentText("86.15"), "86.15%");
    assert.equal(percentText(null), "—");
});

test("list: the two sub-tabs split on the exam's own scope, not its class", () => {
    const rows = splitByScope([
        exam({ id: "a", scope: "class" }),
        exam({ id: "b", scope: "school", classId: null, classroomId: null }),
        exam({ id: "c", scope: "class" }),
    ]);
    assert.deepEqual(
        rows.class.map((item) => item.id),
        ["a", "c"],
    );
    assert.deepEqual(
        rows.school.map((item) => item.id),
        ["b"],
    );

    assert.deepEqual(examStatusChip("draft"), { label: "Draft", tone: "muted" });
    assert.deepEqual(examStatusChip("scheduled"), { label: "Scheduled", tone: "accent" });
    assert.deepEqual(examStatusChip("published"), { label: "Published", tone: "green" });
    // An unknown word is shown, not swallowed.
    assert.deepEqual(examStatusChip("postponed"), { label: "postponed", tone: "muted" });
});

test("dates: they read the same in every locale, and a missing one says so", () => {
    assert.equal(dayText("2026-03-12"), "12 Mar");
    assert.equal(dayText(null), "—");
    assert.equal(dayText("not-a-date"), "—");

    assert.equal(clockText("09:00:00"), "09:00");
    assert.equal(clockText(null), "");

    assert.equal(dateRangeText("2026-03-12", "2026-03-20"), "12 Mar – 20 Mar");
    assert.equal(dateRangeText("2026-03-12", "2026-03-12"), "12 Mar");
    assert.equal(dateRangeText(null, null), "Dates not set");

    assert.equal(
        paperWhenText(paper({})),
        "12 Mar · 09:00–12:00 · Room 4",
        "the paper's own line carries its date, its hours and its room",
    );
    assert.equal(
        paperWhenText(paper({ examDate: null, room: null })),
        "Date to be set · 09:00–12:00",
    );
});

test("progress: published wins, then the count, and nobody is told a lie", () => {
    assert.deepEqual(paperProgress(paper({ publishedAt: "2026-03-21T10:00:00" }), 30), {
        label: "Published",
        tone: "green",
    });
    assert.deepEqual(paperProgress(paper({ marksEntered: 0 }), 30), {
        label: "Not entered",
        tone: "muted",
    });
    assert.deepEqual(paperProgress(paper({ marksEntered: 12 }), 30), {
        label: "12/30 in",
        tone: "amber",
    });
    assert.deepEqual(paperProgress(paper({ marksEntered: 30 }), 30), {
        label: "30/30 in",
        tone: "accent",
    });
    // A caller who cannot know the cohort (a school exam's other classes).
    assert.deepEqual(paperProgress(paper({ marksEntered: 12 }), 0), {
        label: "12 in",
        tone: "amber",
    });
});

test("form: a draft is sent only when it can be saved, and says why not", () => {
    const empty = blankDraft("class", { papers: [blankPaper()] });
    const problems = draftProblems(empty);
    assert.ok(problems.includes("Give the exam a name."));
    assert.ok(
        problems.includes("Add at least one paper to the date sheet."),
        "the untouched starter row is not a paper",
    );
    assert.equal(isBlankPaper(blankPaper()), true);

    const good = blankDraft("class", {
        name: "Unit Test 2",
        papers: [blankPaper({ subjectId: "s1", examDate: "2026-03-12" })],
    });
    assert.deepEqual(draftProblems(good), [], "a name, a subject and a date are enough");

    const tooMuch = blankDraft("class", {
        name: "Unit Test 2",
        startDate: "2026-03-20",
        endDate: "2026-03-12",
        papers: [
            blankPaper({
                subjectId: "s1",
                examDate: "2026-03-12",
                maxMarks: "50",
                passingMarks: "60",
            }),
        ],
    });
    const wrong = draftProblems(tooMuch);
    assert.ok(wrong.includes("Passing marks cannot exceed the paper's maximum."));
    assert.ok(wrong.includes("The exam cannot end before it starts."));

    const noDate = blankDraft("class", {
        name: "Unit Test 2",
        papers: [blankPaper({ subjectId: "s1", maxMarks: "0", examDate: "" })],
    });
    const missing = draftProblems(noDate);
    assert.ok(missing.includes("Every paper needs a date."));
    assert.ok(missing.includes("A paper's maximum must be more than zero."));
});

test("form: a school exam's rows name their class, and no class sits a subject twice", () => {
    const school = blankDraft("school", {
        name: "Annual",
        papers: [blankPaper({ subjectId: "s1", examDate: "2026-03-12" })],
    });
    assert.ok(draftProblems(school).includes("A school exam's paper needs its class."));

    const duplicate = blankDraft("school", {
        name: "Annual",
        papers: [
            blankPaper({ subjectId: "s1", classId: "c10", examDate: "2026-03-12" }),
            blankPaper({ subjectId: "s1", classId: "c10", examDate: "2026-03-13" }),
        ],
    });
    assert.deepEqual(draftProblems(duplicate), ["That class already has a paper in this subject."]);

    const otherClass = blankDraft("school", {
        name: "Annual",
        papers: [
            blankPaper({ subjectId: "s1", classId: "c10", examDate: "2026-03-12" }),
            blankPaper({ subjectId: "s1", classId: "c11", examDate: "2026-03-13" }),
        ],
    });
    assert.deepEqual(draftProblems(otherClass), [], "the same subject in another class is fine");
});

test("sheet: saved rows open pre-filled, and only the lines that changed are sent", () => {
    const edits = editFromRows([
        row({ studentId: "a", marksObtained: "72.50" }),
        row({ studentId: "b", marksObtained: null, absent: true }),
        row({ studentId: "c", marksObtained: null, absent: false }),
    ]);
    assert.deepEqual(
        edits.map((edit) => edit.score),
        ["72.5", "", ""],
    );
    assert.equal(edits[1].absent, true);
    assert.deepEqual(changedEdits(edits), [], "reading a sheet is not a change");

    edits[0].score = "75";
    edits[2].score = "40";
    assert.deepEqual(
        changedEdits(edits).map((edit) => edit.studentId),
        ["a", "c"],
    );
    assert.equal(rowChanged(edits[1]), false, "an untouched absence stays untouched");

    // An absence is not a zero: it carries no score at all.
    edits[0].absent = true;
    const payload = marksEntries(edits);
    assert.deepEqual(payload[0], { student_id: "a", marks_obtained: null, absent: true });
    assert.deepEqual(payload[1], { student_id: "c", marks_obtained: 40, absent: false });
});

test("scores: a blank is allowed, a wrong number explains itself", () => {
    assert.equal(scoreProblem("", "100"), null);
    assert.equal(scoreProblem("   ", "100"), null);
    assert.equal(scoreProblem("72.5", "100"), null);
    assert.equal(scoreProblem("100", "100"), null);
    assert.equal(scoreProblem("101", "100"), "The maximum is 100.");
    assert.equal(scoreProblem("abc", "100"), "Enter a number.");
    assert.equal(scoreProblem("-1", "100"), "A score cannot be negative.");
});

test("publish: the server's own rules, said before the button is pressed", () => {
    const edits = editFromRows([row({ studentId: "a", marksObtained: "72.50" })]);

    assert.deepEqual(publishGate({ paper: paper(), edits, canEdit: false }), {
        allowed: false,
        reason: "Only the paper's teacher or the office can publish.",
    });
    assert.equal(
        publishGate({
            paper: paper({ publishedAt: "2026-03-21T10:00:00" }),
            edits,
            canEdit: true,
        }).allowed,
        false,
    );

    const blank = editFromRows([row({ studentId: "a", marksObtained: null, absent: false })]);
    assert.deepEqual(publishGate({ paper: paper(), edits: blank, canEdit: true }), {
        allowed: false,
        reason: "Enter at least one mark before publishing.",
    });

    const tooHigh = editFromRows([row({ studentId: "a", marksObtained: "140" })]);
    const refused = publishGate({ paper: paper(), edits: tooHigh, canEdit: true });
    assert.equal(refused.allowed, false);
    assert.match(String(refused.reason), /^Aarav: The maximum is 100\.$/);

    assert.deepEqual(publishGate({ paper: paper(), edits, canEdit: true }), {
        allowed: true,
        reason: null,
    });

    test("results: ranks are the school's to give, grades are read, absences are named", () => {
        assert.equal(rankText(1, true), "#1");
        assert.equal(rankText(3, true), "#3");
        assert.equal(rankText(null, true), "—");
        assert.equal(rankText(1, false), "—", "ranks switched off is a dash, never a 1");

        assert.equal(gradeTone("A+"), "green");
        assert.equal(gradeTone("B2"), "accent");
        assert.equal(gradeTone("D"), "amber");
        assert.equal(gradeTone("F"), "red");
        assert.equal(gradeTone(null), "muted");

        test("body: a class exam inherits the page's ids; a school exam's rows carry their own", () => {
            const classBody = draftBody(
                blankDraft("class", {
                    name: "  Unit Test 2  ",
                    papers: [blankPaper({ subjectId: "s1", examDate: "2026-03-12" }), blankPaper()],
                }),
                { classId: "c10", classroomId: "r10" },
            );
            assert.equal(classBody.name, "Unit Test 2", "the name is trimmed");
            assert.equal(classBody.class_id, "c10");
            assert.equal(classBody.classroom_id, "r10");
            assert.equal(classBody.papers.length, 1, "the untouched row is not sent");
            assert.equal(classBody.papers[0].class_id, "c10");
            assert.equal(classBody.papers[0].max_marks, 100);
            assert.equal(classBody.papers[0].passing_marks, 33);
            assert.equal(
                classBody.papers[0].start_time,
                null,
                "a blank time is null, not an empty string",
            );
            assert.equal(classBody.term, null);

            const schoolBody = draftBody(
                blankDraft("school", {
                    name: "Annual",
                    papers: [
                        blankPaper({ subjectId: "s1", classId: "c9", examDate: "2026-03-12" }),
                    ],
                }),
                { classId: "c10", classroomId: "r10" },
            );
            assert.equal(schoolBody.class_id, null);
            assert.equal(schoolBody.classroom_id, null);
            assert.equal(schoolBody.papers[0].class_id, "c9");
        });

        assert.equal(
            markCellText({ obtained: "72.50", absent: false, maxMarks: "100.00" }),
            "72.5/100",
        );
        assert.equal(markCellText({ obtained: null, absent: true, maxMarks: "100.00" }), "Absent");
        assert.equal(markCellText({ obtained: null, absent: false, maxMarks: "100.00" }), "—");

        test("section: only this room's class exams, never a school one", () => {
            const exams = [
                exam({ id: "mine", classroomId: "r10", classId: "c10" }),
                exam({ id: "class-level", classroomId: null, classId: "c10" }),
                exam({ id: "other-room", classroomId: "r11", classId: "c10" }),
                exam({ id: "other-class", classroomId: null, classId: "c9" }),
                exam({ id: "school", scope: "school", classroomId: null, classId: null }),
            ];
            assert.deepEqual(
                forSection(exams, { classroomId: "r10", classId: "c10" }).map((item) => item.id),
                ["mine", "class-level"],
            );
        });

        test("form: a saved exam reopens exactly as it was written", () => {
            const draft = draftFromExam(
                exam({
                    papers: [
                        paper({
                            maxMarks: "80.00",
                            passingMarks: null,
                            startTime: "09:15:00",
                            endTime: null,
                            room: null,
                            chapterIds: ["ch1"],
                        }),
                    ],
                }),
            );
            assert.equal(draft.name, "Mid-Term");
            assert.equal(draft.scope, "class");
            assert.equal(draft.papers.length, 1);
            assert.equal(
                draft.papers[0].startTime,
                "09:15",
                "the seconds the input cannot hold are cut",
            );
            assert.equal(draft.papers[0].endTime, "");
            assert.equal(draft.papers[0].examDate, "2026-03-12");
            assert.equal(draft.papers[0].maxMarks, "80");
            assert.equal(draft.papers[0].passingMarks, "");
            assert.deepEqual(draft.papers[0].chapterIds, ["ch1"]);
            // An exam read back and saved unchanged sends exactly what it was.
            assert.deepEqual(draftProblems(draft), []);
        });

        assert.equal(passText({ passedAll: true, absentCount: 0 }), "All passed");
        assert.equal(passText({ passedAll: true, absentCount: 2 }), "Passed, absent in some");
        assert.equal(passText({ passedAll: false, absentCount: 0 }), "Failed a paper");
        assert.equal(passText({ passedAll: null, absentCount: 0 }), "—");

        const results = {
            unpublished: ["p2"],
            papers: [
                { paperId: "p1", subject: "Mathematics" },
                { paperId: "p2", subject: "Science" },
            ],
        } as unknown as ExamResults;
        assert.deepEqual(unpublishedSubjects(results), ["Science"]);
    });

    // A paper is published with one child absent and one still blank: the school decides.
    const mixed = editFromRows([
        row({ studentId: "a", marksObtained: "72.50" }),
        row({ studentId: "b", marksObtained: null, absent: true }),
        row({ studentId: "c", marksObtained: null, absent: false }),
    ]);
    assert.equal(publishGate({ paper: paper(), edits: mixed, canEdit: true }).allowed, true);
    assert.deepEqual(sheetCounts(mixed), { marked: 1, absent: 1, blank: 1 });
});
