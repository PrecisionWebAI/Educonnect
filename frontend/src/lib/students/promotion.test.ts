import assert from "node:assert/strict";
import { test } from "node:test";

import type { CatalogClass } from "../../types/index.ts";
import {
    doneKindOf,
    isHighestClass,
    lowerClassOf,
    nextYearBlock,
    nextClassOf,
    higherClasses,
    resultMessage,
    studentsLabel,
    undoLabel,
} from "./promotion.ts";

function klass(name: string, level: number): CatalogClass {
    return { id: `id-${level}`, name, level, stage: "", sections: [] };
}

const classes = [klass("Class 8", 8), klass("Class 6", 6), klass("Class 7", 7)];

test("the next class is the next level, whatever order the list came in", () => {
    assert.equal(nextClassOf(classes, "Class 6")?.name, "Class 7");
    assert.equal(nextClassOf(classes, "Class 7")?.name, "Class 8");
});

test("the highest class has no next class and completes instead", () => {
    assert.equal(nextClassOf(classes, "Class 8"), null);
    assert.equal(isHighestClass(classes, "Class 8"), true);
    assert.equal(isHighestClass(classes, "Class 7"), false);
    assert.equal(isHighestClass(classes, "Class 99"), false);
});

test("the picker lists only the classes above the student's own, in order", () => {
    assert.deepEqual(
        higherClasses(classes, "Class 6").map((item) => item.name),
        ["Class 7", "Class 8"],
    );
    assert.deepEqual(
        higherClasses(classes, "Class 7").map((item) => item.name),
        ["Class 8"],
    );
    assert.deepEqual(higherClasses(classes, "Class 8"), []);
    assert.deepEqual(higherClasses(classes, "Class 99"), []);
});

test("class names match without caring about capitals", () => {
    assert.equal(nextClassOf(classes, "class 6")?.name, "Class 7");
    assert.equal(isHighestClass(classes, "CLASS 8"), true);
    assert.deepEqual(
        higherClasses(classes, " class 7 ").map((item) => item.name),
        ["Class 8"],
    );
});

test("labels and the result sentence name what was done and what was skipped", () => {
    assert.equal(studentsLabel(1), "1 student");
    assert.equal(studentsLabel(3), "3 students");
    assert.equal(resultMessage("promoted", { done: 2, skipped: [] }), "2 students promoted.");
    assert.equal(
        resultMessage("promoted", {
            done: 1,
            skipped: [{ studentId: "a", name: "Aarav", reason: "Already has a record." }],
        }),
        "1 student promoted. Skipped 1 - Aarav: Already has a record.",
    );
    assert.equal(resultMessage("promoted", { done: 0, skipped: [] }), "Nobody was promoted.");
});

test("the class below is the one right under, none for the lowest", () => {
    assert.equal(lowerClassOf(classes, "Class 8")?.name, "Class 7");
    assert.equal(lowerClassOf(classes, "class 7")?.name, "Class 6");
    assert.equal(lowerClassOf(classes, "Class 6"), null);
    assert.equal(lowerClassOf(classes, "Class 99"), null);
});

test("what was done to a student is read from the outcome and the moved-from note", () => {
    assert.equal(doneKindOf({ nextYearOutcome: "Promoted to Class 7" }), "promoted");
    assert.equal(doneKindOf({ nextYearOutcome: "Retained in Class 6" }), "retained");
    assert.equal(doneKindOf({ movedFrom: "Class 6-A" }), "moved");
    assert.equal(doneKindOf({}), null);
});

test("a button becomes Undo only when every ticked student has that thing done", () => {
    const retained = { nextYearOutcome: "Retained in Class 6" };
    const fresh = {};
    assert.equal(undoLabel([retained, retained], "retained", "Retain"), "Undo retain");
    assert.equal(undoLabel([retained, fresh], "retained", "Retain"), "Retain");
    assert.equal(undoLabel([], "retained", "Retain"), "Retain");
    assert.equal(undoLabel([{ movedFrom: "Class 6-A" }], "moved", "De-promote"), "Undo de-promote");
});

test("promote and retain wait until the next session exists, and say why", () => {
    const y2026 = { name: "2026-27", startDate: "2026-04-01", endDate: "2027-03-31" };
    const y2027 = { name: "2027-28", startDate: "2027-04-01", endDate: "2028-03-31" };

    // Running year, next one not created: create it from the menu.
    const missing = nextYearBlock([y2026], y2026, "2026-11-23");
    assert.match(missing ?? "", /2027-28\) is not created yet/);
    assert.match(missing ?? "", /Create 2027-28 from the year menu/);

    // Next year exists: nothing blocks.
    assert.equal(nextYearBlock([y2026, y2027], y2026, "2026-11-23"), null);

    // Looking at the latest year while it is not the running one: nothing to create from here.
    const other = nextYearBlock([y2026, y2027], y2027, "2026-11-23");
    assert.match(other ?? "", /only one year after the running year/);

    // No year on screen: nothing to say.
    assert.equal(nextYearBlock([], null, "2026-11-23"), null);
});
