import assert from "node:assert/strict";
import test from "node:test";

import {
    blankPassLine,
    choosePassBy,
    cleanGradeInput,
    isGradeText,
    defaultPassMarks,
    editPassMarks,
    followTotal,
    gradeForPercent,
    passLineBody,
    passLineIssue,
    passMarksPercentText,
    passPercentOf,
    percentText,
    rungOf,
    round2,
    type LadderRung,
} from "./marking.ts";

const LADDER: LadderRung[] = [
    { minPercent: 90, grade: "A1" },
    { minPercent: 80, grade: "A2" },
    { minPercent: 70, grade: "B1" },
    { minPercent: 60, grade: "B2" },
    { minPercent: 50, grade: "C1" },
    { minPercent: 40, grade: "C2" },
    { minPercent: 33, grade: "D" },
    { minPercent: 0, grade: "E" },
];

test("the pass marks start at 33% of the total: 100 -> 33, 50 -> 16.5, 20 -> 6.6", () => {
    assert.equal(defaultPassMarks(100), 33);
    assert.equal(defaultPassMarks(50), 16.5);
    assert.equal(defaultPassMarks(20), 6.6);
});

test("halves round up, and the school's own percentage is respected", () => {
    assert.equal(round2(4.125), 4.13);
    assert.equal(defaultPassMarks(12.5), 4.13);
    assert.equal(defaultPassMarks(100, 40), 40);
});

test("changing the number shows what percent of the total it is: 33 -> 40 on 100 reads 40%", () => {
    assert.equal(passPercentOf(40, 100), 40);
    assert.equal(percentText(passPercentOf(40, 100)), "40%");
    assert.equal(percentText(33.33), "33.33%");
    assert.equal(percentText(16.5), "16.5%");
    assert.equal(passPercentOf(10, 0), null);
    assert.equal(percentText(null), "");
});

test("the pass marks follow the total until the teacher types their own", () => {
    let draft = followTotal(blankPassLine(), 100);
    assert.equal(draft.passMarks, "33");
    draft = followTotal(draft, 50);
    assert.equal(draft.passMarks, "16.5");
    draft = followTotal(draft, 20);
    assert.equal(draft.passMarks, "6.6");

    draft = editPassMarks(draft, "8");
    assert.equal(draft.passMarksEdited, true);
    draft = followTotal(draft, 100);
    assert.equal(draft.passMarks, "8", "a number the teacher typed stays");
});

test("no total means no pre-filled number", () => {
    assert.equal(followTotal(blankPassLine(), null).passMarks, "");
    assert.equal(followTotal(blankPassLine(), 0).passMarks, "");
});

test("the small percent beside the box tracks the number and the total", () => {
    let draft = editPassMarks(blankPassLine(), "40");
    assert.equal(passMarksPercentText(draft, 100), "40%");
    assert.equal(passMarksPercentText(draft, 50), "80%");
    draft = editPassMarks(draft, "");
    assert.equal(passMarksPercentText(draft, 100), "");
    assert.equal(passMarksPercentText(editPassMarks(draft, "40"), null), "");
});

test("a grade is found on the ladder ignoring case; a percentage earns its grade", () => {
    assert.equal(rungOf(LADDER, "d")?.minPercent, 33);
    assert.equal(rungOf(LADDER, "Z"), undefined);
    assert.equal(rungOf(LADDER, "  "), undefined);
    assert.equal(gradeForPercent(LADDER, 92), "A1");
    assert.equal(gradeForPercent(LADDER, 33), "D");
    assert.equal(gradeForPercent(LADDER, 32.99), "E");
    assert.equal(gradeForPercent(LADDER, null), null);
});

test("marks mode: Save needs a total and a number within 0..total", () => {
    const draft = (marks: string) => editPassMarks(blankPassLine(), marks);
    assert.equal(passLineIssue(draft("33"), null, LADDER), "Enter the total marks first.");
    assert.equal(passLineIssue(draft(""), 100, LADDER), "Enter the passing marks.");
    assert.equal(passLineIssue(draft("-1"), 100, LADDER), "Passing marks cannot be below 0.");
    assert.match(passLineIssue(draft("101"), 100, LADDER) ?? "", /more than the total \(100\)/);
    assert.equal(passLineIssue(draft("100"), 100, LADDER), null);
    assert.equal(passLineIssue(draft("40"), 100, LADDER), null);
});

test("a typed grade keeps a capital letter first, then a letter or a digit, two at most", () => {
    assert.equal(cleanGradeInput("a1"), "A1");
    assert.equal(cleanGradeInput("abc"), "AB");
    assert.equal(cleanGradeInput("1a"), "A");
    assert.equal(cleanGradeInput("a-"), "A");
    assert.equal(cleanGradeInput(""), "");
    assert.equal(isGradeText("C1"), true);
    assert.equal(isGradeText("1C"), false);
});

test("a custom grade is a letter, then a letter or a number", () => {
    const base = { ...choosePassBy(blankPassLine(), "grade"), customMinPercent: "35" };
    assert.equal(passLineIssue({ ...base, passingGrade: "P" }, 100, LADDER), null);
    assert.equal(passLineIssue({ ...base, passingGrade: "PQ" }, 100, LADDER), null);
    assert.equal(passLineIssue({ ...base, passingGrade: "C1" }, 100, LADDER), null);
    for (const bad of ["PQR", "1P", "p", "P!"]) {
        assert.match(
            String(passLineIssue({ ...base, passingGrade: bad }, 100, LADDER)),
            /capital letter first/,
        );
    }
    // a ladder grade with a digit is still fine
    assert.equal(passLineIssue({ ...base, passingGrade: "A1" }, 100, LADDER), null);
});

test("grade mode: a ladder grade or a custom one is enough - no percentage is asked", () => {
    const base = choosePassBy(blankPassLine(), "grade");
    assert.equal(passLineIssue(base, 100, LADDER), "Choose the lowest passing grade.");
    assert.equal(passLineIssue({ ...base, passingGrade: "d" }, 100, LADDER), null);
    assert.equal(passLineIssue({ ...base, passingGrade: "P" }, 100, LADDER), null);
});

test("switching Marks/Grade keeps what was typed for the other one", () => {
    let draft = editPassMarks(blankPassLine(), "40");
    draft = { ...choosePassBy(draft, "grade"), passingGrade: "C2" };
    draft = choosePassBy(draft, "marks");
    assert.equal(draft.passMarks, "40");
    assert.equal(draft.passingGrade, "C2");
});

test("the payload carries only the fields of the chosen mode", () => {
    assert.deepEqual(passLineBody(editPassMarks(blankPassLine(), "40")), {
        pass_mode: "marks",
        passing_marks: 40,
        passing_grade: null,
        custom_min_percent: null,
        grade_mode: "na",
    });
    const grade = {
        ...choosePassBy(blankPassLine(), "grade"),
        passingGrade: " P ",
        customMinPercent: "35",
    };
    assert.deepEqual(passLineBody(grade), {
        pass_mode: "grade",
        passing_marks: null,
        passing_grade: "P",
        custom_min_percent: 35,
        grade_mode: "na",
    });
});
