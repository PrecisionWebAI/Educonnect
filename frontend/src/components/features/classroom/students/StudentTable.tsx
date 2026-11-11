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
                    className="group flex w-full cursor-pointer items-center gap-3 rounded-xl p-2 text-left transition-colors hover:bg-(--accent-surface)/50"
                    title="View profile"
                    onClick={() => onView(s)}
                >
                    <div className="bg-primary/20 text-primary flex h-10 w-10 shrink-0 items-center justify-center rounded-full font-bold shadow-sm transition-all group-hover:shadow-[0_0_10px_rgba(var(--primary),0.3)]">
                        {initials(s.name)}
                    </div>
                    <div className="flex min-w-0 flex-col">
                        <strong className="text-foreground truncate text-sm">{s.name}</strong>
                        <span className="text-muted-foreground truncate text-xs">
                            {s.admissionNo}
                        </span>
                    </div>
                </button>
            ),
        },
        {
            key: "className",
            header: "Class",
            // A student with no placement yet has no class to print.
            render: (s) => (s.className ? `${s.className}-${s.section}` : "Not placed"),
        },
        { key: "gender", header: "Gender", render: (s) => s.gender || "—" },
        {
            key: "guardian",
            header: "Guardian",
            render: (s) => (
                <span>
                    {s.guardian || "—"}
                    {s.guardianEmail ? (
                        <>
                            <br />
                            <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>
                                {s.guardianEmail}
                            </span>
                        </>
                    ) : null}
                </span>
            ),
        },
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
                <div className="flex items-center justify-end gap-2">
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onEdit(s)}
                        className="border-(--border-subtle) bg-(--background)/50 backdrop-blur-sm hover:bg-(--accent-surface)"
                    >
                        Edit
                    </Button>
                    <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => onToggleStatus(s)}
                        className="hover:bg-(--accent-surface)"
                    >
                        {s.status === "Active" ? "Deactivate" : "Activate"}
                    </Button>
                </div>
            ),
        },
    ];

    return (
        <div className="glass-card overflow-hidden rounded-2xl border border-(--border-subtle) shadow-sm">
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
