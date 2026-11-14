"use client";
import { Table, Badge, Pagination, type BadgeTone } from "@/components/ui";
import type { StaffMember } from "@/types";

/**
 * The staff directory table.
 *
 * The status badge carries the same three words the API sends (`Active`,
 * `On Leave`, `Inactive`) because the employment state is what a principal is
 * scanning for; `Inactive` used to have no tone of its own and showed as amber,
 * the same colour as "away today".
 */
const STATUS_TONE: Record<StaffMember["status"], BadgeTone> = {
    Active: "green",
    "On Leave": "amber",
    Inactive: "muted",
};

export default function StaffListTable({
    rows,
    totalItems,
    page,
    pageSize,
    onPageChange,
    onRowClick,
}: {
    rows: StaffMember[];
    totalItems?: number;
    page?: number;
    pageSize?: number;
    onPageChange?: (page: number) => void;
    /** Opens the person's profile drawer - the row is the control. */
    onRowClick?: (row: StaffMember) => void;
}) {
    const columns = [
        {
            key: "staffCode",
            header: "ID",
            render: (r: StaffMember) => (
                <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>{r.staffCode}</span>
            ),
        },
        {
            key: "name",
            header: "Name",
            render: (r: StaffMember) => (
                <div className="cell-name">
                    <span className="cell-avatar">
                        {r.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")}
                    </span>
                    <div style={{ lineHeight: 1.2 }}>
                        <div>{r.name}</div>
                        <div style={{ color: "var(--muted)", fontSize: "0.74rem" }}>
                            {/* No subject listed is shown as such - not as the department. */}
                            {r.subject || "No subject assigned"}
                        </div>
                    </div>
                </div>
            ),
        },
        { key: "department", header: "Department" },
        {
            key: "qualification",
            header: "Qualification",
            render: (r: StaffMember) => r.qualification ?? "—",
        },
        {
            key: "classes",
            header: "Classes",
            render: (r: StaffMember) => r.classes.join(", ") || "—",
        },
        {
            key: "workload",
            header: "Workload",
            render: (r: StaffMember) => (
                <span>
                    {r.workload}{" "}
                    <span style={{ color: "var(--muted)", fontSize: "0.74rem" }}>/ wk</span>
                </span>
            ),
        },
        {
            key: "status",
            header: "Status",
            render: (r: StaffMember) => <Badge tone={STATUS_TONE[r.status]}>{r.status}</Badge>,
        },
    ];

    return (
        <div>
            <Table
                columns={columns}
                rows={rows}
                rowKey={(r) => r.id}
                empty="No staff found for the current filters."
                onRowClick={onRowClick}
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
