"use client";

import { Spinner, Table } from "@/components/ui";
import { getSchoolResults } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { ResultRow } from "@/types";

// School-wide exam results: pass rate, average and topper per class, exam by exam.
// It is about every class at once, so it sits on the Classroom grid rather than on
// one class-section's page.

export default function ResultsPanel() {
    const query = useApiQuery(["classroom", "results"], getSchoolResults);
    const rows: ResultRow[] = query.data ?? [];

    if (query.isPending) return <Spinner />;

    return (
        <Table
            columns={[
                { key: "exam", header: "Exam", render: (r: ResultRow) => <b>{r.exam}</b> },
                { key: "className", header: "Class" },
                {
                    key: "passRate",
                    header: "Pass rate",
                    render: (r: ResultRow) => `${r.passRate}%`,
                },
                {
                    key: "avgScore",
                    header: "Avg score",
                    render: (r: ResultRow) => `${r.avgScore}%`,
                },
                { key: "topper", header: "Topper" },
            ]}
            rows={rows}
            rowKey={(r) => r.id}
            empty="No marks entered yet — a row appears once a class has marks in an exam."
        />
    );
}
