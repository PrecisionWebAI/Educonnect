import assert from "node:assert/strict";
import test from "node:test";

import {
    chipLabel,
    closedReasonOn,
    isClosedDay,
    isoDate,
    marksFromRows,
    storedStatus,
    thresholdTone,
    trendBars,
} from "./view.ts";
import type { RegisterRow } from "@/types";

function row(partial: Partial<RegisterRow>): RegisterRow {
    return {
        studentId: "s1",
        recordId: null,
        name: "aarav sharma",
        admissionNo: "P4-1",
        status: "unmarked",
        marked: false,
        remarks: null,
        leaveRequestId: null,
        ...partial,
    };
}

test("preload: only a real mark becomes a chip", () => {
    const marks = marksFromRows([
        row({ studentId: "a", status: "present", marked: true, recordId: "r1" }),
        row({ studentId: "b", status: "absent", marked: true, recordId: "r2" }),
        // Leave is derived from an approved request - it must not be re-sent as a mark.
        row({ studentId: "c", status: "leave", marked: true, leaveRequestId: "l1" }),
        // The picker has no half-day chip, and "unmarked" is the absence of a mark.
        row({ studentId: "d", status: "half_day", marked: true }),
        row({ studentId: "e" }),
    ]);

    assert.deepEqual(marks, { a: "Present", b: "Absent" });
});

test("holiday state: the reason is the school's own words", () => {
    const days = [
        { date: "2026-11-17", reason: "diwali break" },
        { date: "2026-11-22", reason: "Sunday" },
    ];

    assert.equal(closedReasonOn(days, "2026-11-17"), "diwali break");
    assert.equal(closedReasonOn(days, "2026-11-18"), null, "an open day has no reason");
    assert.equal(isClosedDay(days, new Date("2026-11-17T00:00:00")), true);
    assert.equal(isClosedDay(days, new Date("2026-11-18T00:00:00")), false);
    assert.equal(isoDate(new Date("2026-11-18T00:00:00")), "2026-11-18");
});

test("threshold chip: below, at the mark, and no data", () => {
    assert.equal(thresholdTone(74.9, 75), "below");
    assert.equal(thresholdTone(75, 75), "ok", "the threshold is a floor");
    assert.equal(thresholdTone(100, 75), "ok");
    assert.equal(thresholdTone(null, 75), "none", "no data is not 0%");
});

test("trend bars: unmarked days are skipped, never drawn as zero", () => {
    const bars = trendBars([
        { date: "2026-11-16", present: 3, marked: 4, percent: 75 },
        { date: "2026-11-17", present: 0, marked: 0, percent: null },
        { date: "2026-11-18", present: 2, marked: 3, percent: 66.7 },
    ]);

    assert.deepEqual(bars, [
        { label: "Mon", value: 75 },
        { label: "Wed", value: 67 },
    ]);
});

test("chips: stored wording in, chip words out", () => {
    assert.equal(chipLabel("half_day"), "Half day");
    assert.equal(chipLabel("unmarked"), "Unmarked");
    assert.equal(storedStatus("Present"), "present");
    assert.equal(storedStatus("Half day" as never), "half day");
});
