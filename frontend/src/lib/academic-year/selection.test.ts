import assert from "node:assert/strict";
import { test } from "node:test";

import { academicYearHeader, getSelectedYearId, setSelectedYearId } from "./selection.ts";

test("with nothing chosen the running year is wanted and no header is sent", () => {
    setSelectedYearId(null);
    assert.equal(getSelectedYearId(), null);
    assert.deepEqual(academicYearHeader(), {});
});

test("a chosen year rides on every request until it is cleared", () => {
    setSelectedYearId("year-2027");
    assert.equal(getSelectedYearId(), "year-2027");
    assert.deepEqual(academicYearHeader(), { "X-Academic-Year": "year-2027" });
    setSelectedYearId(null);
    assert.deepEqual(academicYearHeader(), {});
});
