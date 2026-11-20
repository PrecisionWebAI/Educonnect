import assert from "node:assert/strict";
import test from "node:test";

import {
    academicYearChipState,
    academicYearLabel,
    academicYearLabelForStart,
    academicYearRange,
    canManageAcademicYear,
    nextAcademicYearStart,
    nextAcademicYearStartAfterCurrent,
} from "./view.ts";
import type { AcademicYear } from "@/types";

function year(name: string, isCurrent = false): AcademicYear {
    return {
        id: name,
        name,
        startDate: `${name.slice(0, 4)}-04-01`,
        endDate: `${Number(name.slice(0, 4)) + 1}-03-31`,
        isCurrent,
    };
}

test("label: current year, missing full and compact", () => {
    assert.equal(academicYearLabel(year("2026-27", true)), "2026-27");
    assert.equal(academicYearLabel(null), "Academic year not set");
    assert.equal(academicYearLabel(null, true), "Not set");
});

test("open label is the next two-year pair", () => {
    assert.equal(academicYearLabelForStart(2026), "2026-27");
    assert.equal(academicYearLabelForStart(2029), "2029-30");
});

test("year shows its dates with month names", () => {
    assert.equal(
        academicYearRange(year("2026-27")),
        "01 Apr 2026 – 31 Mar 2027",
    );
});

test("next year follows the newest opened, else the April boundary", () => {
    assert.equal(nextAcademicYearStart([year("2026-27"), year("2027-28")]), 2028);
    assert.equal(nextAcademicYearStart([], new Date("2026-03-31T12:00:00")), 2025);
    assert.equal(nextAcademicYearStart([], new Date("2026-04-01T12:00:00")), 2026);
});

test("only the year after the current one may be opened", () => {
    assert.equal(nextAcademicYearStartAfterCurrent(year("2026-27", true)), 2027);
    assert.equal(nextAcademicYearStartAfterCurrent(null, new Date("2026-04-01")), 2026);
});

test("chip state: missing is manager/read-only, current is current", () => {
    assert.equal(academicYearChipState(year("2026-27"), false), "current");
    assert.equal(academicYearChipState(null, true), "missing-manager");
    assert.equal(academicYearChipState(null, false), "missing-readonly");
});

test("manager needs both the permission and a role above the principal", () => {
    assert.equal(
        canManageAcademicYear(["academic_year.manage"], ["SCHOOL_ADMIN"]),
        true,
    );
    assert.equal(
        canManageAcademicYear(["academic_year.manage"], ["PRINCIPAL"]),
        false,
    );
    assert.equal(canManageAcademicYear([], ["SCHOOL_ADMIN"]), false);
    assert.equal(canManageAcademicYear(["academic_year.manage"], null), false);
});
