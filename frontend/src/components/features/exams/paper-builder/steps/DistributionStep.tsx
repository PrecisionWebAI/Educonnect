"use client";

// ============================================================
// DistributionStep — blueprint §1.6 + §1.7 merged (inside Step 2:
// Exam Blueprint, panel ②).
// The teacher assigns marks (Mode A) or percentages (Mode B) per
// selected chapter at the CHAPTER level. Anything left unassigned
// becomes a Random bucket — at the chapter level (across chapters)
// and, inside each chapter (opened via its Topics toggle), at the
// TOPIC level within that chapter.
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
    const cap = dist.mode === "marks" ? totalMarks : 100;
    const allocated = distributionAllocated(dist);
    const unit = dist.mode === "marks" ? "marks" : "%";
    const chapterRandom = chapterLevelRandom(dist, totalMarks);
    const overflow = allocated > cap;

    if (dist.chapters.length === 0) {
        return (
            <div className="rounded-md border p-4">
                <p className="text-sm font-semibold">Distribution</p>
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
                <p className="text-sm font-semibold">Distribution</p>
                <Select
                    value={dist.mode}
                    onChange={(e) =>
                        builder.setDistributionMode(e.target.value as DistributionMode)
                    }
                >
                    <option value="marks">Marks per selected chapter</option>
                    <option value="percent">Percentage of selected chapter</option>
                </Select>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
                Assign {unit === "marks" ? "marks" : "percentages"} per chapter. Anything left
                off goes into a <span className="font-medium">Random</span> bucket — at the
                chapter level and, per chapter, at the topic level (open a chapter's toggle to
                split it topic-wise).
            </p>
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
                                    {c.topics.length === 0 && (
                                        <p className="pl-4 text-xs text-muted-foreground">
                                            No topics split yet — add a topic below.
                                        </p>
                                    )}
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
                                        {tRandom > 0 && (
                                            <span className="text-xs text-muted-foreground">
                                                Random inside topic selection:{" "}
                                                <b>
                                                    {tRandom} {unit}
                                                </b>
                                            </span>
                                        )}
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

                {/* chapter-level Random bucket */}
                <div className="flex flex-wrap items-center gap-2 rounded border border-dashed p-2 text-sm">
                    <span className="font-medium">Random (unassigned)</span>
                    <span className="text-muted-foreground">
                        {overflow
                            ? `⚠ Assigned ${allocated} exceeds ${cap} — reduce by ${allocated - cap} ${unit}.`
                            : chapterRandom > 0
                                ? `Left over from the selected chapters — the generator fills these ${chapterRandom} ${unit} from any chapter.`
                                : "Everything assigned — no chapter-level random."}
                    </span>
                    {!overflow && (
                        <span className="ml-auto font-medium tabular-nums">
                            {chapterRandom} {unit}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}