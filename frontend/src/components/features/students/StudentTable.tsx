"use client";

import type { Student } from "@/types";
import { Badge, Button, Table, Pagination, type Column } from "@/components/ui";

function initials(name: string) {
    return name
        .split(" ")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase();
}

export default function StudentTable({
    rows,
    totalItems,
    page,
    pageSize,
    onPageChange,
    onView,
    onEdit,
    onToggleStatus,
}: {
    rows: Student[];
    totalItems?: number;
    page?: number;
    pageSize?: number;
    onPageChange?: (page: number) => void;
    onView: (s: Student) => void;
    onEdit: (s: Student) => void;
    onToggleStatus: (s: Student) => void;
}) {
    const columns: Column<Student>[] = [
        {
            key: "name",
            header: "Student",
            render: (s) => (
                <button
                    type="button"
                    className="cell-name"
                    title="View profile"
                    style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        color: "inherit",
                        padding: 0,
                    }}
                    onClick={() => onView(s)}
                >
                    <span className="cell-avatar">{initials(s.name)}</span>
                    <span>
                        <strong>{s.name}</strong>
                        <br />
                        <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>
                            {s.admissionNo}
                        </span>
                    </span>
                </button>
            ),
        },
        { key: "className", header: "Class", render: (s) => `${s.className}-${s.section}` },
        { key: "gender", header: "Gender" },
        { key: "guardian", header: "Guardian" },
        { key: "phone", header: "Contact" },
        {
            key: "status",
            header: "Status",
            render: (s) => (
                <Badge tone={s.status === "Active" ? "green" : "muted"}>{s.status}</Badge>
            ),
        },
        {
            key: "actions",
            header: "",
            align: "right",
            render: (s) => (
                <span style={{ display: "inline-flex", gap: "0.4rem" }}>
                    <Button size="sm" variant="outline" onClick={() => onEdit(s)}>
                        Edit
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => onToggleStatus(s)}>
                        {s.status === "Active" ? "Deactivate" : "Activate"}
                    </Button>
                </span>
            ),
        },
    ];

    return (
        <div>
            <Table
                columns={columns}
                rows={rows}
                rowKey={(s) => s.id}
                empty="No students match your filters."
            />
            {totalItems !== undefined &&
                page !== undefined &&
                pageSize !== undefined &&
                onPageChange && (
                    <Pagination
                        currentPage={page}
                        totalItems={totalItems}
                        pageSize={pageSize}
                        onPageChange={onPageChange}
                    />
                )}
        </div>
    );
}
