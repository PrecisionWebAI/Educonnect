import assert from "node:assert/strict";
import test from "node:test";

import {
    chipLabel,
    closedReasonOn,
    closedTone,
    coveringRow,
    dayLabel,
    dayModel,
    filterRoster,
    isClosedDay,
    isWeeklyOffReason,
    isoDate,
    marksFromRows,
    monthFigure,
    nthOffLabel,
    rangeLabel,
    storedStatus,
    thresholdTone,
    trendBars,
    withRoll,
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

test("preload: a saved mark becomes a chip, and leave reads as absent", () => {
    const marks = marksFromRows([
        row({ studentId: "a", status: "present", marked: true, recordId: "r1" }),
        row({ studentId: "b", status: "absent", marked: true, recordId: "r2" }),
        // An approved leave is decided elsewhere; here the day is recorded as an absence.
        row({ studentId: "c", status: "leave", marked: true, leaveRequestId: "l1" }),
        // The picker has no half-day chip, and "unmarked" is the absence of a mark.
        row({ studentId: "d", status: "half_day", marked: true }),
        row({ studentId: "e" }),
    ]);

    assert.deepEqual(marks, { a: "Present", b: "Absent", c: "Absent" });
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
        { label: "Mon", date: "2026-11-16", end: "2026-11-16", value: 75, present: 3, marked: 4 },
        { label: "Wed", date: "2026-11-18", end: "2026-11-18", value: 67, present: 2, marked: 3 },
    ]);
});

test("the trend labels come from the server, and the axis never repeats one", () => {
    const bars = trendBars([
        {
            date: "2026-11-02",
            label: "2nd wk Nov",
            present: 8,
            marked: 10,
            percent: 80,
            endDate: "2026-11-08",
        },
        { date: "2026-11-16", label: "Mon", present: 5, marked: 5, percent: 100 },
        { date: "2026-11-23", label: "Mon", present: 4, marked: 5, percent: 80 },
        { date: "2026-11-30", label: "Mon", present: 0, marked: 0, percent: null },
    ]);

    assert.deepEqual(
        bars.map((bar) => bar.label),
        ["2nd wk Nov", "16 Nov", "23 Nov"],
        "a repeated weekday is cut back to its date",
    );
    assert.equal(bars[0].end, "2026-11-08", "a week keeps the day it stops on");
    assert.equal(bars[1].end, "2026-11-16", "a day is its own span");
});

test("chips: stored wording in, chip words out", () => {
    assert.equal(chipLabel("half_day"), "Half day");
    assert.equal(chipLabel("unmarked"), "Unmarked");
    assert.equal(storedStatus("Present"), "present");
    assert.equal(storedStatus("Half day" as never), "half day");
});

test("day model: counts, locked rows and the save state", () => {
    const rows = [
        row({ studentId: "a", status: "present", marked: true }),
        row({ studentId: "b", status: "absent", marked: true }),
        row({ studentId: "c" }),
        row({ studentId: "d" }),
    ];

    const saved = dayModel(rows, {});
    assert.deepEqual(saved.counts, {
        present: 1,
        absent: 1,
        late: 0,
        marked: 2,
        unmarked: 2,
        total: 4,
    });
    assert.equal(saved.savedCount, 2);
    assert.equal(saved.draftCount, 0);
    assert.equal(saved.hasSaved, true);
    assert.equal(saved.isDirty, false);
    assert.deepEqual(
        saved.rows.map((item) => item.locked),
        [true, true, false, false],
        "a saved row is locked until somebody edits it",
    );
    assert.deepEqual(
        saved.rows.map((item) => item.halfDay),
        [false, false, false, false],
    );

    const edited = dayModel(rows, { b: "Present", c: "Late" });
    assert.deepEqual(edited.counts, {
        present: 2,
        absent: 0,
        late: 1,
        marked: 3,
        unmarked: 1,
        total: 4,
    });
    assert.equal(edited.draftCount, 2);
    assert.equal(edited.isDirty, true);
    assert.deepEqual(
        edited.rows.map((item) => item.locked),
        [true, false, false, false],
        "the edited row unlocks; the untouched saved row stays locked",
    );
});

test("day model: a tap is not a save", () => {
    const rows = [row({ studentId: "a" }), row({ studentId: "b" })];
    const fresh = dayModel(rows, {});
    assert.equal(fresh.hasSaved, false);
    assert.equal(fresh.counts.marked, 0);
    assert.equal(fresh.counts.unmarked, 2);

    const tapped = dayModel(rows, { a: "Present" });
    assert.equal(tapped.hasSaved, false, "the cards stay blank until the day is saved");
    assert.equal(tapped.counts.marked, 1, "Marked counts up with the tap");
    assert.equal(tapped.counts.unmarked, 1, "Unmarked counts down with the tap");
});

test("day model: an approved leave is counted as an absence", () => {
    const day = dayModel(
        [
            row({
                studentId: "a",
                status: "leave",
                marked: true,
                leaveRequestId: "l1",
            }),
        ],
        {},
    );
    assert.equal(day.rows[0].mark, "Absent");
    assert.equal(day.counts.absent, 1);
    assert.equal(day.counts.marked, 1);
    assert.equal(day.counts.unmarked, 0);
});

test("a child who left stays on the sheet but out of the counts", () => {
    const rows = [
        row({ studentId: "a", status: "present", marked: true }),
        row({ studentId: "b", active: false }),
        row({ studentId: "c" }),
    ];

    const day = dayModel(rows, {});

    assert.equal(day.rows.length, 3, "the row is never dropped");
    assert.equal(day.rows[1].active, false, "it is flagged instead");
    assert.deepEqual(
        day.counts,
        {
            present: 1,
            absent: 0,
            late: 0,
            marked: 1,
            unmarked: 1,
            total: 2,
        },
        "the cards count the children who are actually in the room",
    );
});

test("roster filter: a search word and a mark narrow the list, never the marks", () => {
    const rows = [
        { studentId: "a", name: "aarav sharma", mark: "Present" as const },
        { studentId: "b", name: "diya patel", mark: "Absent" as const },
        { studentId: "c", name: "aarohi rao", mark: undefined },
    ];

    assert.deepEqual(filterRoster(rows, "", "all"), rows);
    assert.deepEqual(
        filterRoster(rows, "aar", "all").map((row) => row.studentId),
        ["a", "c"],
    );
    assert.deepEqual(
        filterRoster(rows, "", "Absent").map((row) => row.studentId),
        ["b"],
        "the filter looks at the mark the row carries now",
    );
    assert.deepEqual(filterRoster(rows, "diya", "Present"), []);
    assert.deepEqual(
        filterRoster(rows, "", "Late").map((row) => row.studentId),
        [],
        "an unmarked row belongs to no mark filter",
    );
});

test("a weekly off speaks its weekday, a holiday speaks its name", () => {
    assert.equal(isWeeklyOffReason("Sunday"), true);
    assert.equal(isWeeklyOffReason("Saturday"), true);
    assert.equal(isWeeklyOffReason("diwali break"), false);
    assert.equal(isWeeklyOffReason(null), false);
});

test("the month figure is present days over the month's open days", () => {
    assert.equal(monthFigure(12, 27, 22), "Monthly attendance 12/27");
    assert.equal(
        monthFigure(0, 4, 4),
        "Monthly attendance 0/4",
        "zero present is a real answer when the register was taken",
    );
    assert.equal(monthFigure(0, 0, 0), "Monthly attendance —", "no open days is a dash");
    assert.equal(
        monthFigure(0, 27, 0),
        "Monthly attendance —",
        "no register in the month is a dash, not 0/27",
    );
    assert.equal(monthFigure(5, undefined, 5), "Monthly attendance —");
    assert.equal(monthFigure(undefined, 6, 6), "Monthly attendance 0/6");
});

test("roll numbers follow the sheet, not the filter", () => {
    const rows = [
        { studentId: "a", name: "aarav", mark: "Present" as const },
        { studentId: "b", name: "diya", mark: "Absent" as const },
        { studentId: "c", name: "meera", mark: undefined },
    ];
    const numbered = withRoll(rows);

    assert.deepEqual(
        numbered.map((row) => [row.roll, row.name]),
        [
            [1, "aarav"],
            [2, "diya"],
            [3, "meera"],
        ],
        "one number per child, in the server's order",
    );
    assert.deepEqual(
        filterRoster(numbered, "", "Present").map((row) => row.roll),
        [1],
        "a hidden classmate does not renumber the sheet",
    );
});

test("the colour comes from the kind the server sent, never from the words", () => {
    assert.equal(closedTone("holiday"), "holiday");
    assert.equal(closedTone("weekly_off"), "off");
    assert.equal(closedTone("week_off"), "off", "a dated weekly off is still a weekly off");
    assert.equal(closedTone(null), "off");
    assert.equal(closedTone(undefined), "off");
});

test("a Saturday rule reads as the week it closes", () => {
    assert.equal(nthOffLabel("5#1"), "1st Saturday");
    assert.equal(nthOffLabel("5#2"), "2nd Saturday");
    assert.equal(nthOffLabel("5#3"), "3rd Saturday");
    assert.equal(nthOffLabel("5#4"), "4th Saturday");
    assert.equal(nthOffLabel("0#1"), "1st Monday", "the token is not Saturday-only");
    assert.equal(nthOffLabel("nonsense"), "nonsense", "an unreadable token is shown as it is");
});

test("a click on a closed day finds the row that already owns it", () => {
    const rows = [
        { id: "h1", name: "demo", startDate: "2026-10-01", endDate: "2026-10-01" },
        { id: "h2", name: "Diwali break", startDate: "2026-10-28", endDate: "2026-11-02" },
    ];
    assert.equal(coveringRow(rows, "2026-10-01")?.id, "h1", "the holiday itself opens for editing");
    assert.equal(
        coveringRow(rows, "2026-10-30")?.id,
        "h2",
        "a day inside a range opens that range",
    );
    assert.equal(coveringRow(rows, "2026-11-02")?.id, "h2", "the last day of a range is covered");
    assert.equal(coveringRow(rows, "2026-10-02"), null, "an open day is a new holiday");
    assert.equal(coveringRow([], "2026-10-01"), null, "no rows at all is no closure");
});

test("a closure's dates read as one day, or as a range with the year once", () => {
    assert.equal(
        rangeLabel("2026-10-01", "2026-10-01"),
        dayLabel("2026-10-01"),
        "one day prints one date, never 'x - x'",
    );
    const range = rangeLabel("2026-10-01", "2026-10-15");
    assert.equal(range.split("2026").length - 1, 1, "the year appears once, at the end");
    assert.ok(range.endsWith(dayLabel("2026-10-15")), "the range ends on the last day");
    assert.equal(
        rangeLabel("nonsense", "2027-01-02"),
        "nonsense – 2027-01-02",
        "unreadable input is shown as it is",
    );
});
