import assert from "node:assert/strict";
import test from "node:test";

import {
    entryFor,
    entryText,
    groupByExam,
    hasResults,
    passFailText,
    percentGradeText,
    percentOf,
    resultBadge,
    showsGrades,
    showsMarks,
    statsCells,
    subjectColumns,
    subjectOf,
    testLabel,
} from "./results.ts";
import type { OverviewEntry, OverviewStudent, OverviewTest, ResultOverview } from "@/types";

function entry(partial: Partial<OverviewEntry> = {}): OverviewEntry {
    return {
        paperId: "p1",
        obtained: "45.00",
        absent: false,
        percentage: "90.00",
        grade: "A1",
        passed: true,
        ...partial,
    };
}

function paperTest(partial: Partial<OverviewTest> = {}): OverviewTest {
    return {
        paperId: "p1",
        examId: "e1",
        examName: "Class Test - Mathematics",
        examType: "class_test",
        subject: "Mathematics",
        section: "Class 9-A",
        examDate: "2026-12-05",
        totalMarks: "50.00",
        passMode: "marks",
        passPercent: "33.00",
        passingMarks: "16.50",
        passingGrade: null,
        published: true,
        stats: null,
        ...partial,
    };
}

function student(partial: Partial<OverviewStudent> = {}): OverviewStudent {
    return {
        studentId: "s1",
        name: "Aarav",
        admissionNumber: "A1",
        classroomId: "r1",
        section: "Class 9-A",
        entries: [entry()],
        subjects: [
            {
                subject: "Mathematics",
                obtained: "55.00",
                total: "70.00",
                percentage: "78.57",
                grade: "B1",
                testsCounted: 2,
                testsAbsent: 0,
            },
        ],
        overall: {
            obtained: "55.00",
            total: "70.00",
            percentage: "78.57",
            grade: "B1",
            testsCounted: 2,
            testsAbsent: 0,
            testsPassed: 2,
            testsFailed: 0,
        },
        ...partial,
    };
}

test("the display mode decides whether marks, grades or both are shown", () => {
    assert.deepEqual([showsMarks("marks"), showsGrades("marks")], [true, false]);
    assert.deepEqual([showsMarks("grades"), showsGrades("grades")], [false, true]);
    assert.deepEqual([showsMarks("both"), showsGrades("both")], [true, true]);
});

test("a percentage reads without trailing zeros", () => {
    assert.equal(percentOf("90.00"), "90%");
    assert.equal(percentOf("78.5714"), "78.57%");
    assert.equal(percentOf(null), "");
});

test("a percentage and its grade follow the school's display mode", () => {
    assert.equal(percentGradeText("78.57", "B1", "both"), "78.57% · B1");
    assert.equal(percentGradeText("78.57", "B1", "marks"), "78.57%");
    assert.equal(percentGradeText("78.57", "B1", "grades"), "B1");
    assert.equal(percentGradeText(null, null, "both"), "—");
});

test("one test's result reads as marks, percent and grade - or Absent - or a dash", () => {
    assert.equal(entryText(entry(), "50.00", "both"), "45/50 (90%) · A1");
    assert.equal(entryText(entry(), "50.00", "marks"), "45/50 (90%)");
    assert.equal(entryText(entry(), "50.00", "grades"), "A1");
    assert.equal(entryText(entry({ absent: true, obtained: null }), "50.00", "both"), "Absent");
    assert.equal(entryText(entry({ obtained: null, percentage: null }), "50.00", "both"), "—");
    assert.equal(entryText(undefined, "50.00", "both"), "—");
});

test("a zero is a score and reads as one", () => {
    const zero = entry({ obtained: "0.00", percentage: "0.00", grade: "E", passed: false });
    assert.equal(entryText(zero, "50.00", "both"), "0/50 (0%) · E");
});

test("the badge says Pass, Fail or Absent, and nothing when there is nothing to judge", () => {
    assert.deepEqual(resultBadge(entry()), { label: "Pass", tone: "green" });
    assert.deepEqual(resultBadge(entry({ passed: false })), { label: "Fail", tone: "red" });
    assert.deepEqual(resultBadge(entry({ absent: true, passed: null })), {
        label: "Absent",
        tone: "amber",
    });
    assert.equal(resultBadge(entry({ passed: null })), null);
    assert.equal(resultBadge(undefined), null);
});

test("pass and fail counts read as a sentence, or a dash when nothing is counted", () => {
    assert.equal(passFailText(3, 1), "3 passed · 1 failed");
    assert.equal(passFailText(0, 0), "—");
});

test("the class table's subject columns are every subject anyone has, once, alphabetically", () => {
    const a = student();
    const b = student({
        studentId: "s2",
        subjects: [
            { ...a.subjects[0], subject: "science" },
            { ...a.subjects[0], subject: "MATHEMATICS" },
        ],
    });
    assert.deepEqual(subjectColumns([a, b]), ["Mathematics", "science"]);
    assert.equal(subjectOf(b, "mathematics")?.percentage, "78.57", "matched in any case");
    assert.equal(subjectOf(a, "Science"), undefined);
});

test("the tests of one exam are grouped in the order the server sent them", () => {
    const groups = groupByExam([
        paperTest({ paperId: "p1", examId: "e1", examName: "Unit Test" }),
        paperTest({ paperId: "p2", examId: "e1", examName: "Unit Test", subject: "Science" }),
        paperTest({ paperId: "p3", examId: "e2", examName: "Annual" }),
    ]);
    assert.deepEqual(
        groups.map((group) => [group.examName, group.tests.length]),
        [
            ["Unit Test", 2],
            ["Annual", 1],
        ],
    );
});

test("a test is labelled by its subject and date", () => {
    assert.equal(testLabel(paperTest()), "Mathematics · 5 Dec");
    assert.equal(testLabel(paperTest({ examDate: null })), "Mathematics");
});

test("the class view's cells read the figures, and a dash where there are none", () => {
    const cells = statsCells({
        marked: 2,
        absent: 1,
        averageMarks: "27.50",
        averagePercentage: "55.00",
        highest: "45.00",
        lowest: "10.00",
        passed: 1,
        failed: 1,
    });
    assert.deepEqual(cells, {
        marked: "2",
        absent: "1",
        average: "27.5 (55%)",
        highest: "45",
        lowest: "10",
        passed: "1",
        failed: "1",
    });
    assert.equal(statsCells(null).average, "—");
    assert.equal(
        statsCells({
            marked: 0,
            absent: 0,
            averageMarks: null,
            averagePercentage: null,
            highest: null,
            lowest: null,
            passed: 0,
            failed: 0,
        }).highest,
        "—",
    );
});

test("a child's entry is found by its test, and a family sees results only when there are some", () => {
    const one = student();
    assert.equal(entryFor(one, paperTest())?.grade, "A1");
    assert.equal(entryFor(one, paperTest({ paperId: "other" })), undefined);

    const overview: ResultOverview = {
        kind: "class_test",
        academicYearId: null,
        view: "family",
        classroomId: null,
        section: "",
        tests: [],
        students: [one],
        unpublished: 0,
        displayMode: "both",
    };
    assert.equal(hasResults(overview), false);
    assert.equal(hasResults({ ...overview, tests: [paperTest()] }), true);
});
