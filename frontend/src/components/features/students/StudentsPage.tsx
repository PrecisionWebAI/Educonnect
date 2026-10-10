"use client";

import { useMemo, useState } from "react";
import type { Student, ClassMatrixRow } from "@/types";
import { Button, PageHeader, Select, Spinner, Tabs, Badge } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, isParent } from "@/lib/auth/rbac";
import RoleGuard from "@/components/auth/RoleGuard";
import Icon from "@/components/ui/Icon";
import { getClassMatrix } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { useClassCatalog } from "@/hooks/use-class-catalog";
import { useStudents } from "./useStudents";
import StudentTable from "./StudentTable";
import StudentFormModal from "./StudentFormModal";
import StudentProfileSheet from "./StudentProfileSheet";

// Students master data — container (stitch: students_master_data_desktop).
export default function StudentsPage() {
    const toast = useToast();
    const { user } = useAuth();
    const isParentUser = isParent(user?.roles);
    const canManageStudents = hasAnyRole(user?.roles, [
        "SYSTEM_ADMIN",
        "OWNER",
        "PRINCIPAL",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
        "STAFF",
    ]);

    const {
        students,
        filtered,
        paginated,
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

    // The class list comes from the database (`classroom`), in school order
    // (Nursery ... Class 12) - a filter built from the loaded rows would be both
    // incomplete and sorted as text ("Class 1", "Class 10", ...).
    const catalog = useClassCatalog();

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
            return paginated.filter((s) => s.name.includes("Bart") || s.guardian.includes("Homer"));
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
            // Parent **logins** linked to a student - the free-text guardian names
            // would count the same person twice under two spellings, and showed a
            // number that no other screen could agree with.
            value: String(new Set(students.map((s) => s.guardianUserId).filter(Boolean)).size),
        },
        { icon: "school" as const, label: "Classes", value: String(catalog.classNames.length) },
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
                "SYSTEM_ADMIN",
                "OWNER",
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
                            <Button variant="outline" size="sm" icon="⬇">
                                Download CSV
                            </Button>
                        )
                    }
                />

                <Tabs
                    tabs={allowedTabs}
                    active={activeView}
                    onChange={(v) => setView(v as typeof view)}
                />

                {/* stat tiles */}
                {/* stat tiles */}
                <div className="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                    {stats.map((st, i) => {
                        const blobColors = [
                            "blob-blue",
                            "blob-purple",
                            "blob-green",
                            "blob-orange",
                        ];
                        const iconColors = [
                            "text-blue-500 bg-blue-500/10 border-blue-500/20",
                            "text-purple-500 bg-purple-500/10 border-purple-500/20",
                            "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
                            "text-orange-500 bg-orange-500/10 border-orange-500/20",
                        ];

                        return (
                            <div
                                key={st.label}
                                className={`group glass-card hover:shadow-primary/5 relative overflow-hidden rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg ${blobColors[i % blobColors.length]}`}
                            >
                                <div className="relative z-10 mb-4 flex items-start justify-between">
                                    <div className="text-muted-foreground text-xs font-bold tracking-wider uppercase">
                                        {st.label}
                                    </div>
                                    <div
                                        className={`flex h-10 w-10 items-center justify-center rounded-xl border shadow-sm backdrop-blur-md transition-transform duration-500 group-hover:scale-110 group-hover:rotate-6 ${iconColors[i % iconColors.length]}`}
                                    >
                                        <Icon name={st.icon} size={20} />
                                    </div>
                                </div>
                                <div className="relative z-10">
                                    <div className="text-foreground text-4xl font-extrabold tracking-tight drop-shadow-sm">
                                        {st.value}
                                    </div>
                                </div>
                                {/* Decorative element */}
                                <div className="pointer-events-none absolute -right-4 -bottom-4 h-32 w-32 rounded-full bg-gradient-to-br from-white/5 to-transparent blur-2xl transition-transform duration-700 group-hover:scale-150" />
                            </div>
                        );
                    })}
                </div>

                {view === "Class Matrix" ? (
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                        {matrix.length === 0 ? (
                            <div className="text-muted-foreground col-span-full flex flex-col items-center justify-center rounded-3xl border border-(--border-subtle) bg-(--accent-surface)/30 py-16">
                                <Icon name="school" size={48} className="mb-4 opacity-20" />
                                <p>No classes yet.</p>
                            </div>
                        ) : (
                            matrix.map((r: ClassMatrixRow) => (
                                <div
                                    key={r.id}
                                    className="group glass-card blob-blue rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
                                >
                                    <div className="mb-6 flex items-center justify-between border-b border-(--border-subtle)/50 pb-4">
                                        <div className="flex items-center gap-3">
                                            <div className="bg-primary/10 text-primary flex h-10 w-10 items-center justify-center rounded-xl">
                                                <Icon name="groups" size={20} />
                                            </div>
                                            <h3 className="text-foreground text-2xl font-bold">
                                                {r.className}
                                            </h3>
                                        </div>
                                        <Badge
                                            tone={
                                                r.avgAttendance >= 90
                                                    ? "green"
                                                    : r.avgAttendance >= 75
                                                      ? "amber"
                                                      : "red"
                                            }
                                            className="px-2.5 py-1"
                                        >
                                            {r.avgAttendance}% Avg
                                        </Badge>
                                    </div>
                                    <div className="grid grid-cols-3 gap-4">
                                        <div className="rounded-2xl border border-(--border-subtle) bg-(--background)/50 p-4 text-center backdrop-blur-md transition-colors group-hover:bg-(--background)/80">
                                            <div className="text-foreground mb-1 text-2xl font-bold">
                                                {r.strength}
                                            </div>
                                            <div className="text-muted-foreground text-[10px] font-semibold tracking-wider uppercase">
                                                Total
                                            </div>
                                        </div>
                                        <div className="rounded-2xl border border-(--border-subtle) bg-(--background)/50 p-4 text-center backdrop-blur-md transition-colors group-hover:border-blue-500/20 group-hover:bg-blue-500/5">
                                            <div className="mb-1 text-2xl font-bold text-blue-500">
                                                {r.boys}
                                            </div>
                                            <div className="text-muted-foreground text-[10px] font-semibold tracking-wider uppercase">
                                                Boys
                                            </div>
                                        </div>
                                        <div className="rounded-2xl border border-(--border-subtle) bg-(--background)/50 p-4 text-center backdrop-blur-md transition-colors group-hover:border-pink-500/20 group-hover:bg-pink-500/5">
                                            <div className="mb-1 text-2xl font-bold text-pink-500">
                                                {r.girls}
                                            </div>
                                            <div className="text-muted-foreground text-[10px] font-semibold tracking-wider uppercase">
                                                Girls
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                ) : (
                    <>
                        <div className="mb-6 flex flex-col gap-3 rounded-[1.25rem] border border-(--border-subtle) bg-(--card)/40 p-3 shadow-sm backdrop-blur-xl sm:flex-row">
                            <div className="group relative flex-1">
                                <span className="text-muted-foreground group-focus-within:text-primary absolute top-1/2 left-4 -translate-y-1/2 transition-colors">
                                    <Icon name="search" size={18} />
                                </span>
                                <input
                                    className="focus:ring-primary/30 focus:border-primary/50 text-foreground placeholder:text-muted-foreground h-11 w-full rounded-xl border border-(--border-subtle) bg-(--background)/50 pr-4 pl-11 text-sm transition-all hover:bg-(--background)/80 focus:ring-2 focus:outline-none"
                                    placeholder="Search name, admission no, guardian…"
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                />
                            </div>
                            <div className="flex gap-3">
                                <Select
                                    value={classFilter}
                                    onChange={(e) => setClassFilter(e.target.value)}
                                    aria-label="Filter by class"
                                >
                                    <option value="all">All classes</option>
                                    {catalog.classNames.map((c) => (
                                        <option key={c} value={c}>
                                            {c}
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

                <StudentProfileSheet student={profile} onClose={() => setProfile(null)} />
            </div>
        </RoleGuard>
    );
}
