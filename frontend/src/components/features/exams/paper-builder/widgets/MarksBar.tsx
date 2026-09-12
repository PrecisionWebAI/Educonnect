"use client";

// ============================================================
// MarksBar — the live Marks Contract bar from blueprint §1.9.2
// Custom + AI == total, always visible while building a paper.
// ============================================================

const BAR_MAX = 40;

export default function MarksBar({
    total,
    custom,
    ai,
    balance,
    remaining,
    perChapter = undefined,
}: {
    total: number;
    custom: number;
    ai: number;
    balance: number;
    remaining: number;
    perChapter?: { chapter: string; target: number; got: number; ok: boolean }[];
}) {
    const customW = Math.max(2, Math.round((custom / Math.max(1, total)) * BAR_MAX));
    const aiW = Math.max(2, Math.round((ai / Math.max(1, total)) * BAR_MAX));
    const balW = Math.max(0, BAR_MAX - customW - aiW);
    const status = balance === 0
        ? { text: "Balanced ✅", tone: "ok", cls: "bg-emerald-100 text-emerald-800" }
        : balance > 0
            ? { text: `Under by ${balance} — AI budget: ${remaining}`, tone: "warn", cls: "bg-amber-100 text-amber-800" }
            : { text: `Over by ${Math.abs(balance)}`, tone: "bad", cls: "bg-red-100 text-red-700" };

    return (
        <div className="rounded-md border p-4">
            <div className="flex items-center justify-between">
                <span className="text-sm font-medium">
                    Total marks: <b>{total}</b>
                </span>
                <span className={`rounded px-2 py-0.5 text-xs font-medium ${status.cls}`}>
                    {status.text}
                </span>
            </div>
            <div
                className="mt-2 flex h-4 w-full overflow-hidden rounded"
                style={{ display: "flex" }}
            >
                <div
                    className="bg-violet-500"
                    style={{ width: `${customW / BAR_MAX * 100}%` }}
                    title={`Custom ${custom}`}
                />
                <div
                    className="bg-sky-500"
                    style={{ width: `${aiW / BAR_MAX * 100}%` }}
                    title={`AI ${ai}`}
                />
                <div
                    className="bg-zinc-300"
                    style={{ width: `${balW / BAR_MAX * 100}%` }}
                />
            </div>
            <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
                <span>Teacher █ {custom}</span>
                <span>AI █ {ai}</span>
                <span>Budget ░ {remaining}</span>
            </div>
            {perChapter && perChapter.length > 0 && (
                <div className="mt-2 border-t pt-2">
                    <p className="text-xs font-medium text-muted-foreground">Per-chapter (coverage)</p>
                    <ul className="mt-1 grid grid-cols-2 gap-1">
                        {perChapter.map((c) => (
                            <li key={c.chapter} className="text-xs">
                                <span className={c.ok ? "text-emerald-600" : "text-amber-600"}>
                                    {c.ok ? "✅" : "⚠️"}
                                </span>{" "}
                                {c.chapter}: {c.got}/{c.target}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}