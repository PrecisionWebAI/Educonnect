import assert from "node:assert/strict";
import test from "node:test";

import {
    boardCounts,
    feedbackBody,
    gradeGate,
    handedInText,
    marksProblem,
    marksText,
    progressText,
    submissionChip,
} from "./view.ts";
import type { SubmissionItem } from "@/types";

function row(partial: Partial<SubmissionItem> = {}): SubmissionItem {
    return {
        id: "s1",
        homeworkId: "h1",
        homeworkTitle: "Trig worksheet",
        studentId: "st1",
        student: "aarav",
        sectionId: "r1",
        subject: "mathematics",
        status: "Submitted",
        submittedAt: "2026-11-17 10:00",
        isLate: false,
        marksAwarded: null,
        feedback: null,
        gradedAt: null,
        ...partial,
    };
}

test("chip: handed in, late, graded and never handed in are four different things", () => {
    assert.deepEqual(submissionChip(row({})), { label: "Handed in", tone: "green" });
    assert.deepEqual(submissionChip(row({ isLate: true })), { label: "Late", tone: "red" });
    assert.deepEqual(submissionChip(row({ status: "Graded", isLate: true })), {
        label: "Graded · late",
        tone: "violet",
    });
    assert.deepEqual(submissionChip(row({ status: "Graded" })), {
        label: "Graded",
        tone: "violet",
    });
    assert.deepEqual(submissionChip(row({ id: null, status: "Pending" })), {
        label: "Not handed in",
        tone: "muted",
    });
    assert.equal(handedInText(row({})), "2026-11-17 10:00");
    assert.equal(handedInText(row({ submittedAt: "" })), "—");
});

test("board: the three counts a teacher reads, and the 3/4 line", () => {
    const counts = boardCounts([
        row({ id: "a" }),
        row({ id: "b", isLate: true }),
        row({ id: "c", status: "Graded" }),
        row({ id: null, status: "Pending", submittedAt: "" }),
    ]);
    assert.deepEqual(counts, { handedIn: 3, late: 1, pending: 1, graded: 1 });
    assert.equal(progressText({ submitted: 3, total: 4 }), "3/4 in");
    assert.equal(progressText({ submitted: 0, total: 4 }), "0/4 in");
    assert.equal(progressText({ submitted: 0, total: 0 }), "No roll yet");
});

test("marks: homework has no maximum, so only a non-score is refused", () => {
    assert.equal(marksProblem(""), null);
    assert.equal(marksProblem("8.5"), null);
    assert.equal(marksProblem("10"), null);
    assert.equal(marksProblem("-1"), "A score cannot be negative.");
    assert.equal(marksProblem("abc"), "Enter a number.");
    assert.equal(marksProblem("8.555"), "Two decimals at most.");
});

test("gate: nothing to say, or nothing to grade, is refused before the button", () => {
    assert.deepEqual(gradeGate({ marks: "", feedback: "", item: row({}) }), {
        allowed: false,
        reason: "Give a score, a remark, or both.",
    });
    assert.deepEqual(
        gradeGate({ marks: "8", feedback: "", item: row({ id: null, status: "Pending" }) }),
        { allowed: false, reason: "This child has not handed anything in." },
    );
    assert.deepEqual(gradeGate({ marks: "-2", feedback: "ok", item: row({}) }), {
        allowed: false,
        reason: "A score cannot be negative.",
    });
    assert.deepEqual(gradeGate({ marks: "8.5", feedback: "", item: row({}) }), {
        allowed: true,
        reason: null,
    });
    assert.deepEqual(gradeGate({ marks: "", feedback: "Neat work", item: row({}) }), {
        allowed: true,
        reason: null,
    });
});

test("body: blanks become null, and the figures are numbers", () => {
    assert.deepEqual(feedbackBody("8.5", "  Neat work  "), {
        marksAwarded: 8.5,
        feedback: "Neat work",
    });
    assert.deepEqual(feedbackBody("", ""), { marksAwarded: null, feedback: null });
    assert.equal(marksText("8.50"), "8.5");
    assert.equal(marksText(null), "—");
});
