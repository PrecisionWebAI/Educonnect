import assert from "node:assert/strict";
import test from "node:test";

import { draftEntries, withDraftValue, type Draft } from "./draft.ts";

const marked = { employeeId: "a", isMarked: true, status: "present" } as const;
const unmarked = { employeeId: "b", isMarked: false, status: "not_marked" } as const;

test("a changed value is a draft, and choosing the saved one again clears it", () => {
    let draft: Draft = {};
    draft = withDraftValue(draft, marked, "absent");
    assert.deepEqual(draft, { a: "absent" });
    draft = withDraftValue(draft, marked, "present"); // back to what is saved
    assert.deepEqual(draft, {});
});

test("an unmarked person has no saved value, so any choice is a draft", () => {
    const draft = withDraftValue({}, unmarked, "present");
    assert.deepEqual(draft, { b: "present" });
});

test("the draft never mutates the one it was given", () => {
    const before: Draft = { a: "absent" };
    withDraftValue(before, unmarked, "half_day");
    assert.deepEqual(before, { a: "absent" });
});

test("save sends only drafted people, in register order, keeping their remarks", () => {
    const rows = [
        { employeeId: "a", remarks: "medical" },
        { employeeId: "b", remarks: null },
        { employeeId: "c", remarks: "late bus" },
    ];
    const entries = draftEntries(rows, { c: "half_day", a: "absent" });
    assert.deepEqual(entries, [
        { employeeId: "a", status: "absent", remarks: "medical" },
        { employeeId: "c", status: "half_day", remarks: "late bus" },
    ]);
    assert.deepEqual(draftEntries(rows, {}), []);
});
