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
}: {
    rows: StaffProfileRow[];
    onShowLogins: (row: StaffProfileRow) => void;
}) {
    const columns: Column<StaffProfileRow>[] = [
        {
            key: "employeeCode",
            header: "Employee ID",
            render: (r) => <b>{r.employeeCode}</b>,
        },
        { key: "fullName", header: "Name" },
        {
            key: "roleCodename",
            header: "Role",
            render: (r) => staffRoleLabel(r.roleCodename),
        },
        { key: "department", header: "Department" },
        {
            key: "email",
            header: "Login",
            render: (r) => <code className="text-xs break-all">{r.email}</code>,
        },
        { key: "joiningDate", header: "Joined" },
        {
            key: "logins",
            header: "",
            render: (r) => (
                <Button size="sm" variant="outline" onClick={() => onShowLogins(r)}>
                    Logins
                </Button>
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
