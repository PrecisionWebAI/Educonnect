import assert from "node:assert/strict";
import test from "node:test";

import {
    academicYearMonths,
    canReject,
    canSubmitWeek,
    countsLabel,
    defaultPlanMonth,
    missingRequired,
    monthLabel,
    planContent,
    planStatus,
    teachingDaysLabel,
    weekRangeLabel,
} from "./lesson-plan.ts";
import type { LessonPlanContent, LessonPlanWeek } from "@/types";

function week(partial: Partial<LessonPlanWeek>): LessonPlanWeek {
    return {
        planId: "p1",
        weekNo: 1,
        startDate: "2026-11-01",
        endDate: "2026-11-07",
        teachingDays: ["2026-11-02", "2026-11-03"],
        status: null,
        version: 0,
        approvedVersion: null,
        expectedVersion: 0,
        topics: "",
        learningObjectives: "",
        activities: "",
        homework: "",
        resources: "",
        assessment: "",
        approved: null,
        rejectionReason: null,
        submittedAt: null,
        submittedBy: null,
        canEdit: true,
        canRequestChange: false,
        ...partial,
    };
}

function content(partial: Partial<LessonPlanContent>): LessonPlanContent {
    return {
        topics: "Fractions",
        learningObjectives: "Add unlike fractions",
        activities: "",
        homework: "",
        resources: "",
        assessment: "",
        ...partial,
    };
}

test("week header: range and the real teaching days", () => {
    assert.equal(weekRangeLabel(week({})), "1 Nov - 7 Nov");
    assert.equal(teachingDaysLabel(week({})), "2 teaching days");
    assert.equal(teachingDaysLabel(week({ teachingDays: ["2026-11-02"] })), "1 teaching day");
    assert.match(teachingDaysLabel(week({ teachingDays: [] })), /No teaching days/);
    assert.equal(monthLabel(2026, 11), "Nov 2026");
});

test("status: a missing row is not the same as pending approval", () => {
    assert.deepEqual(planStatus(week({})), { label: "Not submitted", tone: "muted" });
    assert.deepEqual(planStatus(week({ status: "Submitted" })), {
        label: "Submitted",
        tone: "amber",
    });
    assert.deepEqual(planStatus(week({ status: "Approved" })), {
        label: "Approved",
        tone: "green",
    });
    assert.deepEqual(planStatus(week({ status: "Rejected" })), {
        label: "Rejected",
        tone: "red",
    });
});

test("required fields: topics and learning objectives, prose preserved", () => {
    assert.equal(missingRequired(content({})), null);
    assert.match(String(missingRequired(content({ topics: "   " }))), /Topics/);
    assert.match(
        String(missingRequired(content({ learningObjectives: "" }))),
        /Learning objectives/,
    );
    assert.equal(planContent(week({ topics: "  Fractions  " })).topics, "  Fractions  ");
});

test("review words: a rejection needs a sentence, counts read submitted then approved", () => {
    assert.equal(canReject(""), false);
    assert.equal(canReject("   "), false);
    assert.equal(canReject("Add the Friday assessment."), true);
    assert.equal(canReject("x".repeat(1001)), false);
    assert.equal(countsLabel(0, 0), "No plan");
    assert.equal(countsLabel(3, 2), "3 submitted · 2 approved");
});

test("submit gate: valid content, and an approved week needs change mode", () => {
    const draft = week({});
    assert.equal(canSubmitWeek(draft, content({}), false), true);
    assert.equal(canSubmitWeek(draft, content({ topics: "" }), false), false);

    const locked = week({
        status: "Approved",
        canEdit: false,
        canRequestChange: true,
    });
    assert.equal(canSubmitWeek(locked, content({}), false), false);
    assert.equal(canSubmitWeek(locked, content({}), true), true);
});

test("an academic year lists April to March, with January-March in the next calendar year", () => {
    const months = academicYearMonths("2026-04-01", "2027-03-31");
    assert.equal(months.length, 12);
    assert.deepEqual([months[0].year, months[0].month, months[0].label], [2026, 4, "April 2026"]);
    assert.deepEqual([months[8].year, months[8].month], [2026, 12]);
    assert.deepEqual([months[9].year, months[9].month], [2027, 1]);
    assert.deepEqual(
        [months[11].year, months[11].month, months[11].label],
        [2027, 3, "March 2027"],
    );
});

test("a shifted year is listed as written", () => {
    const months = academicYearMonths("2026-06-01", "2027-05-31");
    assert.equal(months[0].label, "June 2026");
    assert.equal(months[11].label, "May 2027");
    assert.deepEqual(academicYearMonths("", ""), []);
});

test("the dialog opens on this month when the year contains it, else on the first", () => {
    const months = academicYearMonths("2026-04-01", "2027-03-31");
    assert.equal(defaultPlanMonth(months, { year: 2026, month: 11 })?.label, "November 2026");
    assert.equal(defaultPlanMonth(months, { year: 2028, month: 2 })?.label, "April 2026");
    assert.equal(defaultPlanMonth([], { year: 2026, month: 11 }), null);
});
