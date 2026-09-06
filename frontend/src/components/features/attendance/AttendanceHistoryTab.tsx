"use client";

import type { AttendanceRecord } from "@/types";
import { Badge, Table, Pagination, type Column } from "@/components/ui";

// Read-only attendance history table with pagination.
export default function AttendanceHistoryTab({
    rows,
    totalItems,
    page,
    pageSize,
    onPageChange,
}: {
    rows: AttendanceRecord[];
    totalItems?: number;
    page?: number;
    pageSize?: number;
    onPageChange?: (page: number) => void;
}) {
    const columns: Column<AttendanceRecord>[] = [
        { key: "date", header: "Date" },
        { key: "studentName", header: "Student", render: (r) => <strong>{r.studentName}</strong> },
        { key: "className", header: "Class" },
        {
            key: "status",
            header: "Status",
            render: (r) => (
                <Badge
                    tone={
                        r.status === "Present"
                            ? "green"
                            : r.status === "Absent"
                              ? "red"
                              : r.status === "Late"
                                ? "amber"
                                : "violet"
                    }
                >
                    {r.status}
                </Badge>
            ),
        },
    ];

    return (
        <div>
            <Table
                columns={columns}
                rows={rows}
                rowKey={(r) => r.id}
                empty="No attendance records yet."
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
