import assert from "node:assert/strict";
import test from "node:test";

import { tabStorageKey, tabToRestore } from "./tab-memory.ts";

test("key: the page and its first tab, so a later tab appearing does not change it", () => {
    const before = tabStorageKey("/dashboard/teachers", ["List", "Substitution"]);
    const after = tabStorageKey("/dashboard/teachers", [
        "List",
        "Workload & Performance",
        "Substitution",
    ]);
    assert.equal(before, after);
    assert.notEqual(before, tabStorageKey("/dashboard/staff", ["List", "Substitution"]));
    assert.notEqual(before, tabStorageKey("/dashboard/teachers", ["Register", "Leave"]));
    assert.equal(
        tabStorageKey("/x", ["A"], "mine"),
        "edu-tab:/x:mine",
        "a screen may name its own",
    );
});

test("restore: only a saved tab that exists now and is not already showing", () => {
    const tabs = ["List", "Course", "Substitution"];
    assert.equal(tabToRestore("Substitution", tabs, "List"), "Substitution");
    assert.equal(tabToRestore("List", tabs, "List"), null, "already there");
    assert.equal(tabToRestore("Gone", tabs, "List"), null, "no longer a tab");
    assert.equal(tabToRestore(null, tabs, "List"), null, "nothing saved");
    assert.equal(tabToRestore("", tabs, "List"), null);
});
