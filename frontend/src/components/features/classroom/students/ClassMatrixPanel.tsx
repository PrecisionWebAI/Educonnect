"use client";

import { Badge, Spinner } from "@/components/ui";
import Icon from "@/components/ui/Icon";
import { getClassMatrix } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { ClassMatrixRow } from "@/types";

// School-wide class matrix - strength, boys/girls and average attendance per class.
// It lives on the Classroom grid (it is about every class at once), not on one
// class-section's page.

export default function ClassMatrixPanel() {
    const query = useApiQuery(["academics", "class-matrix"], getClassMatrix);
    const matrix: ClassMatrixRow[] = query.data ?? [];

    if (query.isPending) return <Spinner />;

    if (matrix.length === 0) {
        return (
            <div className="text-muted-foreground flex flex-col items-center justify-center rounded-3xl border border-(--border-subtle) bg-(--accent-surface)/30 py-16">
                <Icon name="school" size={48} className="mb-4 opacity-20" />
                <p>No classes yet.</p>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {matrix.map((r) => (
                <div
                    key={r.id}
                    className="glass-card group relative overflow-hidden rounded-3xl p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg"
                >
                    <div className="mb-5 flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3">
                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-violet-500/20 bg-violet-500/10 text-violet-500">
                                <Icon name="school" size={22} />
                            </div>
                            <h3 className="text-foreground text-2xl font-bold">
                                {r.className}
                            </h3>
                        </div>
                        <Badge
                            tone={
                                r.avgAttendance >= 90
                                    ? "green"
                                    : r.avgAttendance >= 75
                                      ? "amber"
                                      : "red"
                            }
                        >
                            {r.avgAttendance}% Avg
                        </Badge>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                        <div className="rounded-2xl border border-(--border-subtle) bg-(--background)/50 p-4 text-center">
                            <div className="text-foreground mb-1 text-2xl font-bold">
                                {r.strength}
                            </div>
                            <div className="text-muted-foreground text-[10px] font-semibold tracking-wider uppercase">
                                Total
                            </div>
                        </div>
                        <div className="rounded-2xl border border-(--border-subtle) bg-(--background)/50 p-4 text-center">
                            <div className="mb-1 text-2xl font-bold text-blue-500">
                                {r.boys}
                            </div>
                            <div className="text-muted-foreground text-[10px] font-semibold tracking-wider uppercase">
                                Boys
                            </div>
                        </div>
                        <div className="rounded-2xl border border-(--border-subtle) bg-(--background)/50 p-4 text-center">
                            <div className="mb-1 text-2xl font-bold text-pink-500">
                                {r.girls}
                            </div>
                            <div className="text-muted-foreground text-[10px] font-semibold tracking-wider uppercase">
                                Girls
                            </div>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}
