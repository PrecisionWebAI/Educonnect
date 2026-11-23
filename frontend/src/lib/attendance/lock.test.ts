import assert from "node:assert/strict";
import { test } from "node:test";

import { attendanceLock } from "./view.ts";

const year = { name: "2026-27", startDate: "2026-04-01", endDate: "2027-03-31" };

test("inside the year, on a date inside it, nothing is locked", () => {
    const lock = attendanceLock(year, "2026-11-10", "2026-11-23");
    assert.equal(lock.locked, false);
    assert.equal(lock.message, null);
});

test("a previous or next year on screen is read-only for every date", () => {
    const past = attendanceLock(
        { name: "2025-26", startDate: "2025-04-01", endDate: "2026-03-31" },
        "2025-11-10",
        "2026-11-23",
    );
    assert.equal(past.locked, true);
    assert.equal(past.readOnlyYear, true);
    assert.match(past.message ?? "", /2025-26 is read-only/);

    const next = attendanceLock(
        { name: "2027-28", startDate: "2027-04-01", endDate: "2028-03-31" },
        "2027-05-01",
        "2026-11-23",
    );
    assert.equal(next.readOnlyYear, true);
});

test("a date outside the current year is locked with its own message", () => {
    const lock = attendanceLock(year, "2026-03-20", "2026-11-23");
    assert.equal(lock.locked, true);
    assert.equal(lock.outOfYear, true);
    assert.equal(lock.readOnlyYear, false);
    assert.match(lock.message ?? "", /outside 2026-27/);
});

test("with no year open nothing is locked on the client (the server decides)", () => {
    assert.equal(attendanceLock(null, "2026-11-10", "2026-11-23").locked, false);
});
