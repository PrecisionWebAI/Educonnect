import { useMemo, useState } from "react";
import { DonutChart } from "@/components/tremor/DonutChart";
import { BarChart } from "@/components/tremor/BarChart";
import { cn } from "cn";
import { distributionToCoverage, type PaperBuilderApi } from "../usePaperBuilder";

// Chart view options — Bar or Pie (pick one chart at a time).
type ChartView = "bar" | "pie";
// Data scope — aggregate per chapter, or drill down per topic.
type ScopeView = "chapters" | "topics";

const CHART_COLORS = [
    "var(--chart-1)",
    "var(--chart-2)",
    "var(--chart-3)",
    "var(--chart-4)",
    "var(--chart-5)",
];

type ChartRow = {
    [key: string]: string | number;
    name: string;
    "Target marks": number;
    "Actual marks": number;
};

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
    const plan = distributionToCoverage(builder.state.distribution, total);

    const chapterData = useMemo<ChartRow[]>(() => {
        if (plan.chapters.length === 0) return [];
        const actual = builder.coverageChecks;
        return plan.chapters.map((c, i) => ({
            name: c.chapter || `Ch ${i + 1}`,
            "Target marks": c.targetMarks,
            "Actual marks": actual.find((x) => x.chapter === c.chapter)?.got ?? 0,
        }));
    }, [plan.chapters, builder.coverageChecks]);

    const topicData = useMemo<ChartRow[]>(() => {
        if (plan.chapters.length === 0) return [];
        return plan.chapters.flatMap((c) =>
            c.topics.map((t) => ({
                name: `${c.chapter} · ${t.topic}`,
                "Target marks": t.targetMarks,
                "Actual marks":
                    builder.coverageChecks.find((x) => x.chapter === c.chapter)?.got ?? 0,
            })),
        );
    }, [plan.chapters, builder.coverageChecks]);

    const data = scope === "topics" ? topicData : chapterData;
    const topicsEmpty = scope === "topics" && topicData.length === 0;

    if (data.length === 0) {
        return (
            <div className="border-border bg-card/40 rounded-xl border border-dashed p-6 text-center">
                <p className="text-muted-foreground text-sm">
                    {availableChapters.length === 0
                        ? "Select chapters in Step 2 (Source) to see coverage here."
                        : "Assign marks or percentages in the Distribution plan above to see coverage here."}
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
        <div className="space-y-3">
            {/* View toggle — Bar / Pie + scope toggle — Chapters / Topics */}
            <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-foreground text-sm font-semibold">Coverage Charts</h3>
                <div className="flex flex-wrap items-center gap-2">
                    <div className="border-border bg-muted/40 flex rounded-lg border p-0.5">
                        {scopeOptions.map((opt) => (
                            <button
                                key={opt.key}
                                type="button"
                                onClick={() => setScope(opt.key)}
                                className={cn(
                                    "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                                    scope === opt.key
                                        ? "bg-background text-foreground shadow-sm"
                                        : "text-muted-foreground hover:text-foreground",
                                )}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
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
            </div>

            {topicsEmpty ? (
                <div className="border-border bg-card/40 rounded-xl border border-dashed p-6 text-center">
                    <p className="text-muted-foreground text-sm">
                        No topic-level splits in the current distribution plan. Open a chapter's
                        Topics toggle in the Distribution plan above to see topic coverage here.
                    </p>
                </div>
            ) : (
                <div className="border-border bg-card/40 rounded-xl border p-4">
                    <p className="text-muted-foreground mb-2 text-xs">
                        {view === "bar"
                            ? scope === "topics"
                                ? "Marks per topic — Target vs Actual"
                                : "Marks per chapter — Target vs Actual"
                            : scope === "topics"
                                ? "Topic share of total marks"
                                : `Share of total marks (${total} marks)`}
                    </p>
                    {view === "bar" ? (
                        <BarChart
                            data={data}
                            index="name"
                            categories={["Target marks", "Actual marks"]}
                            colors={CHART_COLORS}
                            valueFormatter={(v: number) => `${v} marks`}
                        />
                    ) : (
                        <DonutChart
                            data={data}
                            index="name"
                            category="Target marks"
                            colors={CHART_COLORS}
                            variant="pie"
                            valueFormatter={(v: number) => `${v} marks`}
                        />
                    )}
                </div>
            )}
        </div>
    );
}