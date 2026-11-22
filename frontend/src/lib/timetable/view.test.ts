import assert from "node:assert/strict";
import test from "node:test";

import { cellPeriod, dayRows, gridRows, hhmm, slotLabelAt } from "./view.ts";
import type { BellSlot } from "@/types";
import type { TimetablePeriodItem } from "@/services";

function slot(partial: Partial<BellSlot> = {}): BellSlot {
    return {
        periodNo: 1,
        label: "P1",
        startTime: "08:00:00",
        endTime: "08:45:00",
        isBreak: false,
        ...partial,
    };
}

function period(partial: Partial<TimetablePeriodItem> = {}): TimetablePeriodItem {
    return {
        id: "p1",
        sectionId: "r1",
        classroomSubjectId: "s1",
        teacherId: "e1",
        dayOfWeek: "monday",
        startTime: "08:00",
        endTime: "08:45",
        room: null,
        ...partial,
    };
}

const DEFAULT_DAY: BellSlot[] = [
    slot({ periodNo: 1, label: "P1", startTime: "08:00:00", endTime: "08:45:00" }),
    slot({ periodNo: 2, label: "P2", startTime: "08:45:00", endTime: "09:30:00" }),
    slot({
        periodNo: 3,
        label: "Break",
        startTime: "09:30:00",
        endTime: "09:50:00",
        isBreak: true,
    }),
    slot({ periodNo: 4, label: "P3", startTime: "09:50:00", endTime: "10:35:00" }),
];

test("rows: the school's day, seconds trimmed, breaks in their place", () => {
    assert.equal(hhmm("08:00:00"), "08:00");
    const rows = dayRows(DEFAULT_DAY);
    assert.deepEqual(
        rows.map((row) => row.label),
        ["P1", "P2", "Break", "P3"],
    );
    assert.deepEqual(
        rows.map((row) => row.key),
        ["08:00-08:45", "08:45-09:30", "09:30-09:50", "09:50-10:35"],
    );
    assert.equal(rows[2].isBreak, true);
    // Order is the school's, whatever order the API answered in.
    assert.equal(dayRows([...DEFAULT_DAY].reverse())[0].label, "P1");
});

test("cells: a period lands in the row that starts when it starts", () => {
    const rows = dayRows(DEFAULT_DAY);
    const week = [
        period({ id: "maths", startTime: "08:00", endTime: "08:45" }),
        period({ id: "science", startTime: "09:50", endTime: "10:35", dayOfWeek: "tuesday" }),
    ];
    assert.equal(cellPeriod(week, "monday", rows[0])?.id, "maths");
    assert.equal(cellPeriod(week, "monday", rows[1]), undefined);
    assert.equal(cellPeriod(week, "tuesday", rows[3])?.id, "science");
    // A break row never holds a period, even when one starts at that minute.
    assert.equal(cellPeriod(week, "monday", rows[2]), undefined);
});

test("labels: which bell slot a saved period starts in", () => {
    assert.equal(slotLabelAt(DEFAULT_DAY, "09:50"), "P3");
    assert.equal(slotLabelAt(DEFAULT_DAY, "09:30:00"), "Break");
    assert.equal(slotLabelAt(DEFAULT_DAY, "14:00"), "", "outside the school's day");
});

test("grid: a period the bell schedule does not know still gets a row", () => {
    const rows = gridRows(DEFAULT_DAY, [
        period({ id: "late", startTime: "14:00", endTime: "14:45" }),
    ]);
    assert.equal(rows.length, 5);
    assert.equal(rows[4].start, "14:00");
    assert.equal(rows[4].label, "", "no bell label - it is not one of the school's periods");
    assert.equal(rows[0].label, "P1");
});
