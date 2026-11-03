"use client";

import { Badge, Button, Select, Table } from "@/components/ui";
import type { Column } from "@/components/ui";
import { staffRoleLabel } from "@/services";
import type { HiringCandidateRow, HiringStatus } from "@/types";
import { PIPELINE_STATUSES } from "./useStaffHiring";

// Candidate table. The pipeline stage is changed straight from the Status
// dropdown; the Hired decision is a separate gated button (admin / principal /
// above only) that opens a type-to-confirm modal.

export default function HiringCandidatesTable({
    rows,
    canHire,
    onStatusChange,
    onHire,
}: {
    rows: HiringCandidateRow[];
    canHire: boolean;
    onStatusChange: (row: HiringCandidateRow, status: HiringStatus) => void;
    onHire: (row: HiringCandidateRow) => void;
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
                    {PIPELINE_STATUSES.map((s) => (
                        <option key={s} value={s}>
                            {s}
                        </option>
                    ))}
                </Select>
            </div>
        ),
    };

    const columns: Column<HiringCandidateRow>[] = [
        { key: "candidateName", header: "Candidate" },
        {
            key: "appliedFor",
            header: "Applied For",
            render: (r) => staffRoleLabel(r.appliedFor ?? r.role),
        },
        { key: "department", header: "Department" },
        { key: "subjectName", header: "Subject", render: (r) => r.subjectName || "—" },
        { key: "qualification", header: "Qualification", render: (r) => r.qualification || "—" },
        { key: "experience", header: "Exp (yrs)", render: (r) => String(r.experience) },
        {
            key: "interviewAt",
            header: "Interview",
            render: (r) =>
                r.interviewAt ? new Date(r.interviewAt).toLocaleString() : r.interviewOn ?? "—",
        },
        { key: "email", header: "Email", render: (r) => r.email || "—" },
        { key: "phone", header: "Phone", render: (r) => r.phone || "—" },
        {
            key: "resume",
            header: "Resume",
            render: (r) =>
                r.resumePath ? <Badge tone="green">Uploaded</Badge> : <span className="text-muted-foreground">—</span>,
        },
        statusColumn,
        {
            key: "hire",
            header: "",
            align: "right",
            render: (r) =>
                canHire && r.status !== "Hired" ? (
                    <Button variant="primary" size="sm" onClick={() => onHire(r)}>
                        Hired
                    </Button>
                ) : null,
        },
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
