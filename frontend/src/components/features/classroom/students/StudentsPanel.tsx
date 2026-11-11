"use client";

import { useState } from "react";
import { Select, Spinner } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole } from "@/lib/auth/rbac";
import type { Student } from "@/types";
import { useStudents, type StudentFormValues } from "./useStudents";
import StudentTable from "./StudentTable";
import StudentFormModal from "./StudentFormModal";
import StudentProfileSheet from "./StudentProfileSheet";

// The student directory **inside one class-section**.
//
// Same table, same filters and the same add/edit modal the school-wide screen
// used - but the class-section is fixed by the page it is mounted on, so it opens
// on *that* class's students by default and can never show another section's.

export default function StudentsPanel({
    className,
    section,
}: {
    /** The class the page is showing ("Class 12"). */
    className: string;
    /** The section letter the page is showing ("J"). */
    section: string;
}) {
    const toast = useToast();
    const { user } = useAuth();
    const canManage = hasAnyRole(user?.roles, [
        "SYSTEM_ADMIN",
        "SCHOOL_ADMIN",
        "PRINCIPAL",
        "STAFF",
    ]);

    const s = useStudents({ className, section });
    const [editing, setEditing] = useState<Student | null>(null);
    const [formOpen, setFormOpen] = useState(false);
    const [profile, setProfile] = useState<Student | null>(null);

    if (!s.students) return <Spinner />;

    function handleSubmit(values: StudentFormValues) {
        if (editing) {
            s.updateStudent(editing.id, values);
            toast.push("success", `${values.name || "Student"} updated`);
        } else {
            s.addStudent(values);
            toast.push("success", `${values.name || "Student"} added to ${className}-${section}`);
        }
        setFormOpen(false);
        setEditing(null);
    }

    function handleEdit(row: Student) {
        setEditing(row);
        setFormOpen(true);
    }

    return (
        <div className="space-y-4">
            <div className="flex flex-col gap-3 rounded-[1.25rem] border border-(--border-subtle) bg-(--card)/40 p-3 shadow-sm backdrop-blur-xl sm:flex-row">
                <input
                    className="focus:ring-primary/30 focus:border-primary/50 text-foreground placeholder:text-muted-foreground h-11 w-full flex-1 rounded-xl border border-(--border-subtle) bg-(--background)/50 px-4 text-sm transition-all hover:bg-(--background)/80 focus:ring-2 focus:outline-none"
                    placeholder={`Search ${className}-${section} students…`}
                    value={s.query}
                    onChange={(e) => s.setQuery(e.target.value)}
                />
                <Select
                    value={s.statusFilter}
                    onChange={(e) => s.setStatusFilter(e.target.value)}
                    aria-label="Filter by status"
                >
                    <option value="all">All statuses</option>
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                </Select>
            </div>

            <StudentTable
                rows={s.paginated}
                totalItems={s.totalItems}
                page={s.page}
                pageSize={s.pageSize}
                onPageChange={s.setPage}
                onView={setProfile}
                onEdit={canManage ? handleEdit : () => {}}
                onToggleStatus={canManage ? s.toggleStatus : () => {}}
            />

            {canManage && (
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
    );
}
