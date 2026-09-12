import { useMemo, useState } from "react";
import { DonutChart } from "@/components/tremor/DonutChart";
import { BarChart } from "@/components/tremor/BarChart";
import { cn } from "cn";
import { coverageToMarks, type PaperBuilderApi } from "../usePaperBuilder";

// Chart view options — "both" renders the bar and pie side-by-side at the same
// time from the same dataset.
type ChartView = "bar" | "pie" | "both";

const CHART_COLORS = [
    "var(--chart-1)",
    "var(--chart-2)",
    "var(--chart-3)",
    "var(--chart-4)",
    "var(--chart-5)",
];

export default function CoverageCharts({
    builder,
    availableChapters,
}: {
    builder: PaperBuilderApi;
    availableChapters: string[];
}) {
    const [view, setView] = useState<ChartView>("both");

    const total = builder.state.basics.totalMarks;
    const plan = builder.state.coverage;

    // TEMP: hard-coded demo numbers so the charts are always visible.
    // Remove once real coverage planning is wired end-to-end.
    const DEMO = [
        { chapter: "Ch 1 — Microorganisms", targetMarks: 8, got: 7 },
        { chapter: "Ch 2 — Metals & Non-metals", targetMarks: 10, got: 10 },
        { chapter: "Ch 3 — Force & Pressure", targetMarks: 6, got: 4 },
        { chapter: "Ch 4 — Light", targetMarks: 6, got: 6 },
    ];

    const isDemo = plan.mode === "auto" || plan.chapters.length === 0;

    const data = useMemo(() => {
        if (isDemo) {
            return DEMO.map((d) => ({
                name: d.chapter,
                "Target marks": d.targetMarks,
                "Actual marks": d.got,
            }));
        }

        const converted = coverageToMarks(plan.mode, plan.chapters, total);
        const actual = builder.coverageChecks;

        return converted.map((c, i) => {
            const a = actual.find((x) => x.chapter === c.chapter);
            return {
                name: c.chapter || `Ch ${i + 1}`,
                "Target marks": c.targetMarks,
                "Actual marks": a ? a.got : 0,
            };
        });
    }, [isDemo, plan.mode, plan.chapters, total, builder.coverageChecks]);

    // No per-chapter plan and no demo data → friendly empty state.
    if (data.length === 0) {
        return (
            <div className="border-border bg-card/40 rounded-xl border border-dashed p-6 text-center">
                <p className="text-muted-foreground text-sm">
                    Coverage charts appear once you switch to{" "}
                    <span className="text-foreground font-medium">Marks-wise</span> or{" "}
                    <span className="text-foreground font-medium">Percentage-wise</span> mode and
                    add chapters. In <span className="text-foreground font-medium">Auto</span> mode
                    marks are distributed across all{" "}
                    <span className="text-foreground font-medium">{availableChapters.length}</span>{" "}
                    chapters automatically.
                </p>
            </div>
        );
    }

    const viewOptions: { key: ChartView; label: string }[] = [
        { key: "bar", label: "Bar" },
        { key: "pie", label: "Pie" },
        { key: "both", label: "Both" },
    ];

    return (
        <div className="space-y-3">
            {/* View toggle — Bar / Pie / Both */}
            <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-foreground text-sm font-semibold">
                    Coverage Charts
                    {isDemo && (
                        <span className="bg-amber-100 text-amber-800 ml-2 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide">
                            Demo data
                        </span>
                    )}
                </h3>
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

            {/* "both" = grid so bar + pie show together at the same time */}
            <div
                className={cn(
                    "grid gap-4",
                    view === "both" ? "grid-cols-1 lg:grid-cols-2" : "grid-cols-1",
                )}
            >
                {view !== "pie" && (
                    <div className="border-border bg-card/40 rounded-xl border p-4">
                        <p className="text-muted-foreground mb-2 text-xs">
                            Marks per chapter — Target vs Actual
                        </p>
                        <BarChart
                            data={data}
                            index="name"
                            categories={["Target marks", "Actual marks"]}
                            colors={CHART_COLORS}
                            valueFormatter={(v: number) => `${v} marks`}
                        />
                    </div>
                )}
                {view !== "bar" && (
                    <div className="border-border bg-card/40 rounded-xl border p-4">
                        <p className="text-muted-foreground mb-2 text-xs">
                            Share of total marks ({total} marks)
                        </p>
                        <DonutChart
                            data={data}
                            index="name"
                            category="Target marks"
                            colors={CHART_COLORS}
                            variant="pie"
                            valueFormatter={(v: number) => `${v} marks`}
                        />
                    </div>
                )}
            </div>
        </div>
    );
}
