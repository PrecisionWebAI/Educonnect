import assert from "node:assert/strict";
import test from "node:test";

import { inr, inrCompact, pct } from "./format.ts";

//: Phase 10 - the three display formatters every screen shares. The point of the
//: move is that there is **one** answer to "what does 90.5 look like", so these
//: assertions are what stops a fourth copy growing back inside a component.

test("a percentage keeps one decimal and carries its sign", () => {
    assert.equal(pct(90.5), "90.5%");
    assert.equal(pct(90.56), "90.6%", "one decimal, rounded");
    assert.equal(pct(90.04), "90%", "a trailing .0 is dropped");
    assert.equal(pct(100), "100%", "a whole number prints without a trailing .0");
    assert.equal(pct(0), "0%", "zero is a real percentage");
});

test("no percentage is a dash, never zero", () => {
    assert.equal(pct(null), "—");
});

test("rupees are grouped the Indian way", () => {
    assert.equal(inr(54600), "₹54,600");
    assert.equal(inr(0), "₹0");
});

test("compact rupees shorten a tile without losing the order of magnitude", () => {
    assert.equal(inrCompact(425000), "₹4.3L");
    assert.equal(inrCompact(100000), "₹1.0L");
    assert.equal(inrCompact(9800), "₹10K");
    assert.equal(inrCompact(640), "₹640");
});

test("the compact boundaries stay where the cards always drew them", () => {
    assert.equal(inrCompact(999), "₹999");
    assert.equal(inrCompact(1000), "₹1K");
    assert.equal(inrCompact(99999), "₹100K");
});

test("no money is a dash, never ₹0", () => {
    assert.equal(inrCompact(null), "—");
});
