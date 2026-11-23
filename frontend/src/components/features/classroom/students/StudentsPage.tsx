"use client";

import { useEffect, useMemo, useState } from "react";
import type { Student } from "@/types";
import { Button, PageHeader, Select, Spinner } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, isParent, isStudent } from "@/lib/auth/rbac";
import RoleGuard from "@/components/auth/RoleGuard";
import Icon from "@/components/ui/Icon";
import { useClassCatalog } from "@/hooks/use-class-catalog";
import { useApiQuery } from "@/lib/api/use-api-query";
import { getStudentsPage, getStudent } from "@/services";
import { errorMessage } from "@/lib/api/client";
import { useStudents } from "./useStudents";
import StudentTable from "./StudentTable";
import StudentFormModal from "./StudentFormModal";
import StudentProfileSheet from "./StudentProfileSheet";

// Students master data — container (stitch: students_master_data_desktop).
export default function StudentsPage() {
    const toast = useToast();
    const { user } = useAuth();
    const isParentUser = isParent(user?.roles);
    const isStudentUser = isStudent(user?.roles);
    const canManageStudents = hasAnyRole(user?.roles, [
        "SYSTEM_ADMIN",
        "SCHOOL_ADMIN",
        "PRINCIPAL",
        "STAFF",
    ]);

    const {
        students,
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
        save,
        setStatus,
    } = useStudents();

    // The class list comes from the database (`classroom`), in school order
    // (Nursery ... Class 12) - a filter built from the loaded rows would be both
    // incomplete and sorted as text ("Class 1", "Class 10", ...).
    const catalog = useClassCatalog();

    const [editing, setEditing] = useState<Student | null>(null);
    const [formOpen, setFormOpen] = useState(false);
    const [profile, setProfile] = useState<Student | null>(null);

    const [error, setError] = useState<string | null>(null);

    /**
     * `?student=<id>` opens that child's profile sheet.
     *
     * The Attendance tab's "Attention Required" list links here, so following a flag
     * lands on the person it is about instead of a search box. The child is fetched by
     * id rather than looked up in the current page, because the flag may be for someone
     * the directory's current page/filter does not show. Read from `window.location`
     * inside an effect rather than `useSearchParams`: the query string is a hint, and a
     * client page should not need a Suspense boundary to read one.
     */
    useEffect(() => {
        const focus = new URLSearchParams(window.location.search).get("student");
        if (!focus) return;
        let cancelled = false;
        getStudent(focus)
            .then((row) => {
                if (!cancelled) setProfile(row);
            })
            .catch(() => {
                // A stale link is not an error worth a toast: the directory still works.
            });
        return () => {
            cancelled = true;
        };
    }, []);

    // The page the server sent. The parent/student view narrows it to their own
    // record, which is the same rule the backend applies to a family's data - the
    // school-wide roll is never drawn for them.
    const displayStudents = useMemo(() => {
        if (!isParentUser && !isStudentUser) return students ?? [];
        return (students ?? []).filter(
            (s) =>
                Boolean(user?.id) && (s.guardianUserId === user?.id || s.user_id === user?.id),
        );
    }, [students, isParentUser, isStudentUser, user]);

    const displayTotalItems = isParentUser || isStudentUser ? displayStudents.length : totalItems;

    // Two true counts for the tiles: the server answers how many are on the roll and
    // how many have left (one row each, so the request stays tiny). Counting the
    // loaded page instead would have described 10 of 917 students.
    const activeCount = useApiQuery(["students", "count", "Active"], () =>
        getStudentsPage({ status: "Active", limit: 1 }),
    );
    const inactiveCount = useApiQuery(["students", "count", "Inactive"], () =>
        getStudentsPage({ status: "Inactive", limit: 1 }),
    );

    if (!students) return <Spinner />;

    /** "no data" is a dash, never an invented zero (rule 4). */
    const countLabel = (value: number | null | undefined) =>
        value === null || value === undefined ? "—" : String(value);

    // stitch stat tiles (SVG icons, no emoji)
    const stats = [
        { icon: "groups" as const, label: "Total Students", value: String(totalItems) },
        {
            icon: "active" as const,
            label: "Active",
            value: countLabel(activeCount.data?.total),
        },
        {
            icon: "guardian" as const,
            label: "Inactive",
            value: countLabel(inactiveCount.data?.total),
        },
        { icon: "school" as const, label: "Classes", value: String(catalog.classNames.length) },
    ];

    function handleEdit(s: Student) {
        setEditing(s);
        setFormOpen(true);
    }

    async function handleSubmit(values: Parameters<typeof save>[0]) {
        setError(null);
        try {
            await save(values, editing?.id);
            toast.push("success", editing ? `${values.name} updated` : `${values.name} admitted`);
            setFormOpen(false);
            setEditing(null);
        } catch (cause) {
            const message = errorMessage(cause, "Could not save the student");
            setError(message);
            toast.push("error", message);
        }
    }

    async function handleToggle(s: Student) {
        setError(null);
        try {
            await setStatus(s);
            toast.push(
                "success",
                s.status === "Active"
                    ? `${s.name} is off the roll`
                    : `${s.name} is back on the roll`,
            );
        } catch (cause) {
            const message = errorMessage(cause, "Could not change the roll status");
            setError(message);
            toast.push("error", message);
        }
    }

    return (
        <RoleGuard
            allowedRoles={["SYSTEM_ADMIN", "SCHOOL_ADMIN", "PRINCIPAL", "STAFF", "GUARDIAN"]}
        >
            <div className="page">
                <PageHeader
                    title={isParentUser ? "My Child Profile" : "Students Directory"}
                    subtitle={
                        isParentUser
                            ? "View your child's academic record and class information"
                            : `${totalItems} ${totalItems === 1 ? "student" : "students"} on the roll`
                    }
                    actions={
                        canManageStudents && (
                            <Button variant="outline" size="sm" icon="⬇">
                                Download CSV
                            </Button>
                        )
                    }
                />

                {error && <p className="mb-4 text-sm text-red-500">{error}</p>}

                {/* stat tiles */}
                {/* stat tiles */}
                <div className="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                    {stats.map((st, i) => {
                        const iconColors = [
                            "text-primary bg-primary/10 border-primary/20",
                            "text-accent-foreground bg-accent border-accent-foreground/20",
                            "text-chart-3 bg-chart-3/10 border-chart-3/20",
                            "text-accent-2 bg-accent-2/10 border-accent-2/20",
                        ];

                        return (
                            <div
                                key={st.label}
                                className="group glass-card relative overflow-hidden rounded-2xl p-6"
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

                {canManageStudents && (
                    <StudentFormModal
                        open={formOpen}
                        editing={editing}
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
