"use client";

import { Button, Table } from "@/components/ui";
import type { Column } from "@/components/ui";
import { staffRoleLabel } from "@/services";
import type { StaffProfileRow } from "@/types";

// The Hired tab: the staff the school actually has - one row per `staffprofile`,
// carrying the login and the employee code the registration created.
//
// "Logins" reopens the credentials panel for a hire whose password note has gone
// missing; a password is never stored in the clear, so the panel offers Reset.

export default function HiredStaffTable({
    rows,
    onShowLogins,
    onEdit,
}: {
    rows: StaffProfileRow[];
    onShowLogins: (row: StaffProfileRow) => void;
    onEdit: (row: StaffProfileRow) => void;
}) {
    const columns: Column<StaffProfileRow>[] = [
        {
            key: "employeeCode",
            header: "Employee ID",
            render: (r) => <b>{r.employeeCode}</b>,
        },
        { key: "fullName", header: "Name" },
        {
            key: "roleCodenames",
            header: "Role",
            render: (r) =>
                (r.roleCodenames.length > 0 ? r.roleCodenames : [r.roleCodename])
                    .map(staffRoleLabel)
                    .join(", "),
        },
        { key: "department", header: "Department" },
        {
            key: "phone",
            header: "Phone",
            render: (r) => r.phone || "—",
        },
        {
            key: "salaryMonthly",
            header: "Salary",
            render: (r) => (r.salaryMonthly != null ? `₹${r.salaryMonthly.toLocaleString()}` : "—"),
        },
        {
            key: "email",
            header: "Login",
            render: (r) => <code className="text-xs break-all">{r.email}</code>,
        },
        { key: "joiningDate", header: "Joined" },
        {
            key: "actions",
            header: "",
            align: "right",
            render: (r) => (
                <div className="flex gap-1">
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onEdit(r)}
                    >
                        Edit
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onShowLogins(r)}
                    >
                        Logins
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
            empty="No staff hired yet - register a hire on the Registration tab."
        />
    );
}
