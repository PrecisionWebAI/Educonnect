"use client";

import { Button, Table } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { AdmissionApplicationRow } from "@/types";
import { primaryGuardian } from "./admission-options";

// Half-filled applications — "Resume" loads the draft into the
// Application tab, "View" opens it read-only.

export default function DraftApplicationsTable({
    rows,
    onResume,
    onView,
}: {
    rows: AdmissionApplicationRow[];
    onResume: (row: AdmissionApplicationRow) => void;
    onView: (row: AdmissionApplicationRow) => void;
}) {
    const columns: Column<AdmissionApplicationRow>[] = [
        { key: "studentFirstName", header: "First Name" },
        { key: "studentLastName", header: "Last Name" },
        { key: "guardian", header: "Guardian", render: primaryGuardian },
        { key: "class", header: "Class", render: (r) => r.appliedForClassLevel || "—" },
        { key: "section", header: "Section", render: (r) => r.appliedSectionPreference || "—" },
        { key: "createdOn", header: "Started On" },
        {
            key: "actions",
            header: "",
            render: (r) => (
                <div className="flex flex-wrap items-center gap-2">
                    <Button variant="primary" size="sm" onClick={() => onResume(r)}>
                        Resume
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => onView(r)}>
                        View
                    </Button>
                </div>
            ),
        },
    ];

    return (
        <Table
            columns={columns}
            rows={rows}
            rowKey={(r) => r.id}
            empty="No draft applications match this filter."
        />
    );
}
