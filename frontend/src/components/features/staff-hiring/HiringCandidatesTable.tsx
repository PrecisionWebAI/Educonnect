"use client";

import { Select, Table } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { HiringCandidateRow, HiringStatus } from "@/types";
import { HIRING_STATUSES } from "./useStaffHiring";

// Candidate table. The pipeline stage is changed straight from the Status
// dropdown (no separate badge, no Actions column). The Employee ID column
// only makes sense once someone is hired, so it shows on the Hired tab.

export default function HiringCandidatesTable({
    rows,
    showEmployeeId,
    onStatusChange,
}: {
    rows: HiringCandidateRow[];
    showEmployeeId: boolean;
    onStatusChange: (row: HiringCandidateRow, status: HiringStatus) => void;
}) {
    const statusColumn: Column<HiringCandidateRow> = {
        key: "status",
        header: "Status",
        render: (r) => (
            <div style={{ minWidth: "8.75rem" }}>
                <Select
                    value={r.status}
                    aria-label={`Status for ${r.candidateName}`}
                    onChange={(e) => onStatusChange(r, e.target.value as HiringStatus)}
                >
                    {HIRING_STATUSES.map((s) => (
                        <option key={s} value={s}>
                            {s}
                        </option>
                    ))}
                </Select>
            </div>
        ),
    };

    const columns: Column<HiringCandidateRow>[] = [
        ...(showEmployeeId
            ? [
                  {
                      key: "empId",
                      header: "Employee ID",
                      render: (r: HiringCandidateRow) => <b>{r.empId || "—"}</b>,
                  } satisfies Column<HiringCandidateRow>,
              ]
            : []),
        { key: "candidateName", header: "Candidate" },
        { key: "role", header: "Vacancy" },
        { key: "department", header: "Department" },
        { key: "qualification", header: "Qualification" },
        { key: "experience", header: "Exp (yrs)", render: (r) => String(r.experience) },
        { key: "interviewOn", header: "Interview" },
        statusColumn,
    ];

    return (
        <Table
            columns={columns}
            rows={rows}
            rowKey={(r) => r.id}
            empty="No candidates match this filter."
        />
    );
}
