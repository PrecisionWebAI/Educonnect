"use client";

// ============================================================
// DistributionStep — blueprint §1.6 + §1.7 merged (inside Step 2:
// Exam Blueprint, panel ②): "Marks Distribution".
// Dropdown ke 3 modes:
//   · Default          → neeche kuch nahi (generator khud decide karta hai)
//   · Mark-Wise        → har chapter ke marks (cap = paper ke Total Marks)
//   · Percentage-Wise  → har chapter ka % (cap = 100%)
// Teacher values fill karke Save karta hai — uske baad hi Step 3 ka
// Marks / Percentage Coverage card + charts aata hai. Jo hissa
// unassigned rehta hai woh Random (unassigned) bucket hai: chapter
// level par, aur chapter ke andar (Topics toggle) topic level par.
// ============================================================

import { Button, Select } from "@/components/ui";
import type { DistributionMode } from "@/types/exam-builder";
import type { PaperBuilderApi } from "../usePaperBuilder";
import {
    chapterLevelRandom,
    distributionAllocated,
    topicAllocated,
    topicLevelRandom,
} from "../usePaperBuilder";

export default function DistributionStep({ builder }: { builder: PaperBuilderApi }) {
    const dist = builder.state.distribution;
    const totalMarks = builder.state.basics.totalMarks;
    const isDefault = dist.mode === "default";
    const cap = dist.mode === "percent" ? 100 : totalMarks;
    const allocated = distributionAllocated(dist);
    const unit = dist.mode === "percent" ? "%" : "marks";
    // random = jo hissa kisi chapter ko assign nahi hua (Random bucket)
    const random = chapterLevelRandom(dist, totalMarks);
    const randomMarks = dist.mode === "percent" ? Math.round((random / 100) * totalMarks) : random;
    const overflow = allocated > cap;
    const topicOverflow = dist.chapters.some((c) => topicAllocated(c) > c.assigned);
    const canSave = !overflow && !topicOverflow && allocated > 0;

    /** Save button ka hint — kya baaki hai. */
    function saveStatus(): string {
        if (overflow) {
            return `Assigned ${allocated} exceeds ${cap} ${unit} — reduce by ${allocated - cap}.`;
        }
        if (topicOverflow) return `Topic values exceed a chapter's ${unit} — fix them, then Save.`;
        if (allocated === 0) return `Fill at least one chapter's ${unit}, then Save.`;
        return `${allocated} of ${cap} ${unit} assigned, ${random} ${unit} unassigned.`;
    }

    if (dist.chapters.length === 0) {
        return (
            <div className="rounded-md border p-4">
                <p className="text-sm font-semibold">Marks Distribution</p>
                <p className="mt-1 text-sm text-muted-foreground">
                    Select chapters in Step 2 (Source) to distribute {totalMarks} marks
                    across them.
                </p>
            </div>
        );
    }

    return (
        <div className="rounded-md border p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold">Marks Distribution</p>
                <Select
                    value={dist.mode}
                    onChange={(e) =>
                        builder.setDistributionMode(e.target.value as DistributionMode)
                    }
                >
                    <option value="default">By AI</option>
                    <option value="marks">Mark-Wise</option>
                    <option value="percent">Percentage-Wise</option>
                </Select>
            </div>

            {!isDefault && (
                <div className="mt-3 grid gap-1.5">
                {dist.chapters.map((c, idx) => {
                    const tSum = topicAllocated(c);
                    const tRandom = topicLevelRandom(c);
                    const tOver = tSum > c.assigned;
                    return (
                        <div key={c.chapter} className="rounded border p-2">
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="w-36 truncate text-sm font-medium">
                                    {c.chapter}
                                </span>
                                <label className="flex items-center gap-1 text-sm">
                                    <span className="text-muted-foreground">{unit}</span>
                                    <input
                                        type="number"
                                        min={0}
                                        step={dist.mode === "percent" ? 0.5 : 1}
                                        className="border-input h-8 w-16 rounded-md border bg-transparent px-2 text-right text-sm"
                                        value={c.assigned === 0 ? "" : String(c.assigned)}
                                        placeholder="0"
                                        onChange={(e) =>
                                            builder.updateChapterDistribution(idx, {
                                                assigned: Math.max(0, Number(e.target.value) || 0),
                                            })
                                        }
                                    />
                                </label>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => builder.toggleChapterTopics(c.chapter)}
                                >
                                    {c.open ? "Topics ▴" : "Topics ▾"}
                                </Button>
                                <span className="text-muted-foreground ml-auto text-xs">
                                    {c.assigned === 0
                                        ? "unassigned → Random"
                                        : `${c.assigned} ${unit} → topics ${tSum}${
                                              tRandom > 0 ? ` · Random ${tRandom}` : ""
                                          }`}
                                </span>
                            </div>
{c.open && (
                                <div className="mt-2 grid gap-1 border-t pt-2">
                                    {c.topics.map((t, ti) => (
                                        <div
                                            key={ti}
                                            className="flex flex-wrap items-center gap-2 pl-4 text-sm"
                                        >
                                            <input
                                                type="text"
                                                placeholder="Topic name — e.g. Photosynthesis"
                                                value={t.topic}
                                                onChange={(e) =>
                                                    builder.updateTopic(c.chapter, ti, {
                                                        topic: e.target.value,
                                                    })
                                                }
                                                className="border-input h-8 w-48 rounded-md border bg-transparent px-2 text-sm"
                                            />
                                            <label className="flex items-center gap-1">
                                                <span className="text-muted-foreground">{unit}</span>
                                                <input
                                                    type="number"
                                                    min={0}
                                                    step={dist.mode === "percent" ? 0.5 : 1}
                                                    className="border-input h-8 w-16 rounded-md border bg-transparent px-2 text-right text-sm"
                                                    value={t.assigned === 0 ? "" : String(t.assigned)}
                                                    placeholder="0"
                                                    onChange={(e) =>
                                                        builder.updateTopic(c.chapter, ti, {
                                                            assigned: Math.max(
                                                                0,
                                                                Number(e.target.value) || 0,
                                                            ),
                                                        })
                                                    }
                                                />
                                            </label>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => builder.removeTopic(c.chapter, ti)}
                                            >
                                                ✕
                                            </Button>
                                        </div>
                                    ))}
<div className="flex flex-wrap items-center gap-2 pl-4">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => builder.addTopic(c.chapter, "")}
                                        >
                                            + Add topic
                                        </Button>
                                        {tOver && (
                                            <span className="text-xs text-red-500">
                                                Topics exceed {c.assigned} {unit} — lower the
                                                topic values or leave the rest as Random.
                                            </span>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}

                {/* Random (unassigned) — label left, remaining value opposite side */}
                <div className="flex items-center justify-between gap-2 rounded border border-dashed p-2 text-sm">
                    <span className="font-medium">Random (unassigned)</span>
                    <span className="font-medium tabular-nums">
                        {dist.mode === "percent"
                            ? `${random}% · ${randomMarks} marks`
                            : `${random} marks`}
                    </span>
                </div>

                {/* Save — values fill karke save karne ke baad hi coverage card aata hai */}
                <div className="mt-1 flex flex-wrap items-center justify-between gap-2 border-t pt-3">
                    <p className="text-muted-foreground text-xs">{saveStatus()}</p>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="primary"
                            size="sm"
                            disabled={!canSave || dist.saved}
                            onClick={() => builder.saveDistribution()}
                        >
                            Save
                        </Button>
                    </div>
                </div>
                </div>
            )}
        </div>
    );
}