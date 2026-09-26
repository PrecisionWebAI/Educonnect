import { useMemo, useState } from "react";
import { DonutChart } from "@/components/tremor/DonutChart";
import { BarChart } from "@/components/tremor/BarChart";
import { cn } from "cn";
import {
    chapterLevelRandom,
    distributionToCoverage,
    type PaperBuilderApi,
} from "../usePaperBuilder";

// Chart view options — Bar ya Pie (ek time par ek chart).
type ChartView = "bar" | "pie";
// Data scope — per chapter, ya chapter ke andar topic-wise.
type ScopeView = "chapters" | "topics";

/** High-contrast palette — light aur dark dono theme me clearly dikhti hai. */
const CHAPTER_COLORS = [
    "#2563eb", // blue
    "#16a34a", // green
    "#f59e0b", // amber
    "#a855f7", // purple
    "#0891b2", // cyan
    "#ec4899", // pink
    "#84cc16", // lime
    "#f97316", // orange
];

/** Target vs Actual bars (chapter scope). */
const TARGET_COLOR = "#2563eb";
const ACTUAL_COLOR = "#16a34a";

/** Unassigned (Random) bucket ka color — hamesha red. */
const UNASSIGNED_COLOR = "#dc2626";
const UNASSIGNED_LABEL = "Random (unassigned)";

/** Ek hue ke halke shades — topic bar/pie se dikhe ki kis chapter ka hai. */
function shade(hex: string, amount: number): string {
    const n = Number.parseInt(hex.slice(1), 16);
    const mix = (c: number) => Math.round(c + (255 - c) * amount);
    return `#${[mix((n >> 16) & 255), mix((n >> 8) & 255), mix(n & 255)]
        .map((c) => c.toString(16).padStart(2, "0"))
        .join("")}`;
}

function chapterColor(index: number): string {
    return CHAPTER_COLORS[index % CHAPTER_COLORS.length];
}

type ChartRow = { [key: string]: string | number; name: string };

interface TopicSlice {
    name: string;
    marks: number;
    chapterIdx: number;
    topicIdx: number;
}

export default function CoverageCharts({
    builder,
    availableChapters,
}: {
    builder: PaperBuilderApi;
    availableChapters: string[];
}) {
    const [view, setView] = useState<ChartView>("bar");
    const [scope, setScope] = useState<ScopeView>("chapters");

    const total = builder.state.basics.totalMarks;
    const engine = builder.state.distribution;
    const plan = distributionToCoverage(engine, total);

    // jo marks kisi chapter ko assign nahi hue — wahi Random (unassigned) bucket
    const leftover = chapterLevelRandom(engine, total);
    const leftoverMarks =
        engine.mode === "percent" ? Math.round((leftover / 100) * total) : leftover;

    // Topics toggle sirf tab dikhta hai jab plan me topics split hue hon
    const hasTopics = plan.chapters.some((c) => c.topics.length > 0);
    const activeScope: ScopeView = scope === "topics" && hasTopics ? "topics" : "chapters";

    /** Chapter rows + unke colors (Random row hamesha red). */
    const chapters = useMemo(() => {
        const actual = builder.coverageChecks;
        const rows: ChartRow[] = plan.chapters.map((c, i) => ({
            name: c.chapter || `Ch ${i + 1}`,
            "Target marks": c.targetMarks,
            "Actual marks": actual.find((x) => x.chapter === c.chapter)?.got ?? 0,
        }));
        const colors = plan.chapters.map((_, i) => chapterColor(i));
        if (leftoverMarks > 0) {
            rows.push({
                name: UNASSIGNED_LABEL,
                "Target marks": leftoverMarks,
                "Actual marks": 0,
            });
            colors.push(UNASSIGNED_COLOR);
        }
        return { rows, colors };
    }, [plan.chapters, builder.coverageChecks, leftoverMarks]);

    /** Topic slices — chapter ke hue ka shade (bar + pie dono me). */
    const topics = useMemo(() => {
        const slices: TopicSlice[] = [];
        plan.chapters.forEach((c, chapterIdx) => {
            c.topics.forEach((t, topicIdx) => {
                slices.push({
                    name: `${c.chapter} · ${t.topic || `Topic ${topicIdx + 1}`}`,
                    marks: t.targetMarks,
                    chapterIdx,
                    topicIdx,
                });
            });
        });
        const colorOf = (s: TopicSlice) =>
            shade(chapterColor(s.chapterIdx), Math.min(s.topicIdx, 4) * 0.2);
        return { slices, colorOf };
    }, [plan.chapters]);

    /** Topic bars — har chapter ka EK full bar (height = chapter target):
     *  uske topics stacked + jo split nahi hua (red). Bina topic wale chapter
     *  bhi full red bar banke aate hain (pie view jaisa) taaki har chapter ka
     *  bar dikhe. Har row me har category ki key pehle se 0 hoti hai —
     *  recharts stack me `undefined` NaN fail karta hai. */
    const topicBars = useMemo(() => {
        const labels: { label: string; color: string }[] = [];
        topics.slices.forEach((s) => {
            if (!labels.some((l) => l.label === s.name)) {
                labels.push({ label: s.name, color: topics.colorOf(s) });
            }
        });
        const topicsSum = (c: { topics: { targetMarks: number }[] }) =>
            c.topics.reduce((n, t) => n + t.targetMarks, 0);
        // koi bhi marks bina topic split ke reh gaye (chapter-level ya andar ka)
        const anyUnassigned =
            leftoverMarks > 0 ||
            plan.chapters.some((c) => c.targetMarks > topicsSum(c));
        if (anyUnassigned) labels.push({ label: UNASSIGNED_LABEL, color: UNASSIGNED_COLOR });

        const rows: ChartRow[] = plan.chapters.map((c, i) => {
            const row: ChartRow = { name: c.chapter || `Ch ${i + 1}` };
            labels.forEach((l) => {
                row[l.label] = 0;
            });
            c.topics.forEach((t, topicIdx) => {
                const label = `${c.chapter} · ${t.topic || `Topic ${topicIdx + 1}`}`;
                row[label] = Number(row[label] ?? 0) + t.targetMarks;
            });
            // chapter ke target tak bar FULL karne wala red remainder
            row[UNASSIGNED_LABEL] = Math.max(0, c.targetMarks - topicsSum(c));
            return row;
        });
        if (leftoverMarks > 0) {
            const row: ChartRow = { name: UNASSIGNED_LABEL };
            labels.forEach((l) => {
                row[l.label] = 0;
            });
            row[UNASSIGNED_LABEL] = leftoverMarks;
            rows.push(row);
        }
        return {
            rows,
            categories: labels.map((l) => l.label),
            colors: labels.map((l) => l.color),
        };
    }, [plan.chapters, topics, leftoverMarks]);

    /** Pie slices — chapters ya topics, har slice ka apna color (unassigned red).
     *  Topic view me red slice = chapter-level unassigned + jo topics me split na hua. */
    const pie = useMemo(() => {
        if (activeScope === "topics" && topics.slices.length > 0) {
            const data: ChartRow[] = topics.slices.map((s) => ({
                name: s.name,
                "Target marks": s.marks,
            }));
            const colors = topics.slices.map((s) => topics.colorOf(s));
            // red slice = jo bhi marks kisi topic ko assign nahi hue
            // (chapter-level unassigned + chapter ke andar unsplit + bina topic wale chapter)
            const topicAssigned = topics.slices.reduce((sum, s) => sum + s.marks, 0);
            const unassigned = Math.max(0, total - topicAssigned);
            if (unassigned > 0) {
                data.push({ name: UNASSIGNED_LABEL, "Target marks": unassigned });
                colors.push(UNASSIGNED_COLOR);
            }
            return { data, colors };
        }
        return { data: chapters.rows, colors: [...chapters.colors] };
    }, [activeScope, topics, chapters, total]);

    if (chapters.rows.length === 0) {
        return (
            <div className="border-border bg-card/40 rounded-xl border border-dashed p-6 text-center">
                <p className="text-muted-foreground text-sm">
                    {availableChapters.length === 0
                        ? "Select chapters in Step 2 (Source) to see coverage here."
                        : "Pick Mark-Wise or Percentage-Wise in the Distribution plan above to see coverage here."}
                </p>
            </div>
        );
    }

    const viewOptions: { key: ChartView; label: string }[] = [
        { key: "bar", label: "Bar" },
        { key: "pie", label: "Pie" },
    ];
    const scopeOptions: { key: ScopeView; label: string }[] = [
        { key: "chapters", label: "Chapters" },
        { key: "topics", label: "Topics" },
    ];

    return (
        <div className="grid gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
                {/* Topics toggle sirf tab jab kisi chapter me topics split hue hon */}
                {hasTopics ? (
                    <div className="border-border bg-muted/40 flex rounded-lg border p-0.5">
                        {scopeOptions.map((opt) => (
                            <button
                                key={opt.key}
                                type="button"
                                onClick={() => setScope(opt.key)}
                                className={cn(
                                    "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                                    activeScope === opt.key
                                        ? "bg-background text-foreground shadow-sm"
                                        : "text-muted-foreground hover:text-foreground",
                                )}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                ) : (
                    <span />
                )}
                <div className="border-border bg-muted/40 flex rounded-lg border p-0.5">
                    {viewOptions.map((opt) => (
                        <button
                            key={opt.key}
                            type="button"
                            onClick={() => setView(opt.key)}
                            className={cn(
                                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                                view === opt.key
                                    ? "bg-background text-foreground shadow-sm"
                                    : "text-muted-foreground hover:text-foreground",
                            )}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="border-border bg-card/40 rounded-xl border p-4">
                <p className="text-muted-foreground mb-2 text-xs">
                    {view === "bar"
                        ? activeScope === "topics"
                            ? "Marks per topic — stacked inside each chapter (red = unassigned)"
                            : "Marks per chapter — Target vs Actual (red = unassigned)"
                        : activeScope === "topics"
                          ? `Topic share of total marks (${total} marks)`
                          : `Share of total marks (${total} marks)`}
                </p>
                {view === "bar" ? (
                    activeScope === "topics" ? (
                        <BarChart
                            data={topicBars.rows}
                            index="name"
                            categories={topicBars.categories}
                            colors={topicBars.colors}
                            stacked
                            valueFormatter={(v: number) => `${v} marks`}
                        />
                    ) : (
                        <BarChart
                            data={chapters.rows}
                            index="name"
                            categories={["Target marks", "Actual marks"]}
                            colors={[TARGET_COLOR, ACTUAL_COLOR]}
                            cellColors={(rowIndex) =>
                                chapters.rows[rowIndex]?.name === UNASSIGNED_LABEL
                                    ? UNASSIGNED_COLOR
                                    : undefined
                            }
                            valueFormatter={(v: number) => `${v} marks`}
                        />
                    )
                ) : (
                    <DonutChart
                        data={pie.data}
                        index="name"
                        category="Target marks"
                        colors={pie.colors}
                        variant="pie"
                        valueFormatter={(v: number) => `${v} marks`}
                    />
                )}
            </div>
        </div>
    );
}
