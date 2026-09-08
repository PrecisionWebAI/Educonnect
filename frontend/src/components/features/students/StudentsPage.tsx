"use client";

import { useEffect, useMemo, useState } from "react";
import type { Student, ClassMatrixRow } from "@/types";
import { Button, PageHeader, Select, Spinner, Table, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, isParent } from "@/lib/auth/rbac";
import RoleGuard from "@/components/auth/RoleGuard";
import Icon from "@/components/ui/Icon";
import { getClassMatrix } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { useStudents } from "./useStudents";
import StudentTable from "./StudentTable";
import StudentFormModal from "./StudentFormModal";
import StudentProfileModal from "./StudentProfileModal";

// Students master data — container (stitch: students_master_data_desktop).
export default function StudentsPage() {
    const toast = useToast();
    const { user } = useAuth();
    const isParentUser = isParent(user?.roles);
    const canManageStudents = hasAnyRole(user?.roles, [
        "ADMIN",
        "DIRECTOR",
        "PRINCIPAL",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
        "STAFF",
    ]);

    const {
        students,
        filtered,
        paginated,
        classes,
        query,
        setQuery,
        classFilter,
        setClassFilter,
        statusFilter,
        setStatusFilter,
        page,
        setPage,
        pageSize,
        totalItems,
        nextAdmissionNo,
        addStudent,
        updateStudent,
        toggleStatus,
    } = useStudents();

    const [editing, setEditing] = useState<Student | null>(null);
    const [formOpen, setFormOpen] = useState(false);
    const [profile, setProfile] = useState<Student | null>(null);

    const allowedTabs = useMemo(() => {
        if (isParentUser) return ["Directory" as const];
        return ["Directory" as const, "Class Matrix" as const];
    }, [isParentUser]);

    const [view, setView] = useState<"Directory" | "Class Matrix">("Directory");
    const activeView = allowedTabs.includes(view) ? view : allowedTabs[0];

    const matrixQuery = useApiQuery(["academics", "class-matrix"], getClassMatrix, {
        enabled: canManageStudents,
    });
    const matrix = matrixQuery.data ?? [];

    const displayStudents = useMemo(() => {
        if (isParentUser) {
            return paginated.filter(
                (s) => s.name.includes("Bart") || s.guardian.includes("Homer"),
            );
        }
        return paginated;
    }, [paginated, isParentUser]);

    const displayTotalItems = isParentUser ? displayStudents.length : totalItems;

    if (!students) return <Spinner />;

    // stitch stat tiles (SVG icons, no emoji)
    const stats = [
        { icon: "groups" as const, label: "Total Students", value: String(students.length) },
        {
            icon: "guardian" as const,
            label: "Guardians",
            value: String(new Set(students.map((s) => s.guardian)).size),
        },
        { icon: "school" as const, label: "Classes", value: String(classes.length) },
        {
            icon: "active" as const,
            label: "Active",
            value: String(students.filter((s) => s.status === "Active").length),
        },
    ];

    function handleEdit(s: Student) {
        setEditing(s);
        setFormOpen(true);
    }

    function handleSubmit(values: Parameters<typeof addStudent>[0]) {
        if (editing) {
            updateStudent(editing.id, values);
            toast.push("success", `${values.name} updated`);
        } else {
            addStudent(values);
            toast.push("success", `${values.name} admitted 🎉`);
        }
        setFormOpen(false);
        setEditing(null);
    }

    function handleToggle(s: Student) {
        toggleStatus(s);
        toast.push("info", `${s.name} marked ${s.status === "Active" ? "Inactive" : "Active"}`);
    }

    return (
        <RoleGuard
            allowedRoles={[
                "ADMIN",
                "DIRECTOR",
                "PRINCIPAL",
                "CLASS_TEACHER",
                "SUBJECT_TEACHER",
                "STAFF",
                "GUARDIAN",
            ]}
        >
            <div className="page">
                <PageHeader
                    title={isParentUser ? "My Child Profile" : "Students Directory"}
                    subtitle={
                        isParentUser
                            ? "View your child's academic record and class information"
                            : `${filtered.length} of ${students.length} students`
                    }
                    actions={
                        canManageStudents && (
                            <>
                                <Button variant="outline" size="sm" icon="⬇">
                                    Download CSV
                                </Button>
                                <Button
                                    icon="＋"
                                    onClick={() => {
                                        setEditing(null);
                                        setFormOpen(true);
                                    }}
                                >
                                    Add student
                                </Button>
                            </>
                        )
                    }
                />

                <Tabs
                    tabs={allowedTabs}
                    active={activeView}
                    onChange={(v) => setView(v as typeof view)}
                />

            {/* stat tiles */}
            <div className="kpi-grid" style={{ marginBottom: "1.2rem" }}>
                {stats.map((st) => (
                    <div key={st.label} className="stat">
                        <span className="stat-ico">
                            <Icon name={st.icon} size={20} />
                        </span>
                        <div className="stat-value">{st.value}</div>
                        <div className="stat-label">{st.label}</div>
                    </div>
                ))}
            </div>

            {view === "Class Matrix" ? (
                <Table
                    columns={[
                        {
                            key: "className",
                            header: "Class",
                            render: (r: ClassMatrixRow) => <b>{r.className}</b>,
                        },
                        { key: "strength", header: "Strength" },
                        { key: "boys", header: "Boys" },
                        { key: "girls", header: "Girls" },
                        {
                            key: "avgAttendance",
                            header: "Avg attendance",
                            render: (r: ClassMatrixRow) => `${r.avgAttendance}%`,
                        },
                    ]}
                    rows={matrix}
                    rowKey={(r) => r.id}
                    empty="No classes yet."
                />
            ) : (
                <>
                    <div className="toolbar">
                        <div className="toolbar-search">
                            <input
                                className="input"
                                placeholder="Search name, admission no, guardian…"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                            />
                        </div>
                        <Select
                            value={classFilter}
                            onChange={(e) => setClassFilter(e.target.value)}
                            aria-label="Filter by class"
                        >
                            <option value="all">All classes</option>
                            {classes.map((c) => (
                                <option key={c} value={c}>
                                    Class {c}
                                </option>
                            ))}
                        </Select>
                        <Select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            aria-label="Filter by status"
                        >
                            <option value="all">All statuses</option>
                            <option value="Active">Active</option>
                            <option value="Inactive">Inactive</option>
                        </Select>
                    </div>

                    <StudentTable
                        rows={displayStudents}
                        totalItems={displayTotalItems}
                        page={page}
                        pageSize={pageSize}
                        onPageChange={setPage}
                        onView={setProfile}
                        onEdit={canManageStudents ? handleEdit : () => {}}
                        onToggleStatus={canManageStudents ? handleToggle : () => {}}
                    />
                </>
            )}

            {canManageStudents && (
                <StudentFormModal
                    open={formOpen}
                    editing={editing}
                    defaultAdmissionNo={nextAdmissionNo()}
                    onClose={() => {
                        setFormOpen(false);
                        setEditing(null);
                    }}
                    onSubmit={handleSubmit}
                />
            )}

            <StudentProfileModal student={profile} onClose={() => setProfile(null)} />
            </div>
        </RoleGuard>
    );
}
