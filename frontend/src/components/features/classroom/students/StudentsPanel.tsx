"use client";

import { useState } from "react";
import { Select, Spinner } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { usePermission } from "@/hooks/use-authorization";
import { useApiQuery } from "@/lib/api/use-api-query";
import { useAcademicYear } from "@/providers/academic-year-context";
import { useClassCatalog } from "@/hooks/use-class-catalog";
import {
    doneKindOf,
    lowerClassOf,
    nextYearBlock,
    resultMessage,
    undoLabel,
} from "@/lib/students/promotion";
import {
    completeStudents,
    getAcademicYears,
    demoteStudents,
    previewUndo,
    promoteStudents,
    retainStudents,
    undoStudents,
} from "@/services";
import type { CatalogClass, PromotionResult, Student } from "@/types";
import { useStudents } from "./useStudents";
import PromoteBar from "./PromoteBar";
import StudentTable from "./StudentTable";
import StudentProfileSheet from "./StudentProfileSheet";

// The student directory **inside one class-section**.
//
// Same table, same filters and the same add/edit modal the school-wide screen used -
// but the class-section is fixed by the page it is mounted on, so it opens on *that*
// class's students by default and can never show another section's.
//
// Every button writes to the database now (the audit's finding): the modal saves
// through `PATCH`/`POST`, "Deactivate"/"Activate" are the lifecycle routes, and the
// list is re-read afterwards - a refresh no longer loses a child.

export default function StudentsPanel({
    className,
    section,
    sectionId,
}: {
    /** The class the page is showing ("Class 12"). */
    className: string;
    /** The section letter the page is showing ("J"). */
    section: string;
    /** The class-section's id - the same one the Attendance tab reads its roll with. */
    sectionId?: string;
}) {
    const toast = useToast();

    const s = useStudents({ className, section, classroomId: sectionId });
    const canPromote = usePermission("students.promote");
    const catalog = useClassCatalog();
    // Promote and Retain move students into the next session, so it must exist first.
    const { current: viewedYear } = useAcademicYear();
    const yearsQuery = useApiQuery(["academic-year", "years"], getAcademicYears, {
        enabled: canPromote,
    });
    const blockedReason = yearsQuery.data
        ? nextYearBlock(yearsQuery.data, viewedYear, new Date().toISOString().slice(0, 10))
        : null;
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [allIds, setAllIds] = useState<string[] | null>(null);
    const [acting, setActing] = useState(false);
    const [profile, setProfile] = useState<Student | null>(null);
    const [error, setError] = useState<string | null>(null);

    if (!s.students) return <Spinner />;

    const allSelected = s.totalItems > 0 && selected.size >= s.totalItems;

    function toggleOne(student: Student) {
        setSelected((current) => {
            const next = new Set(current);
            if (next.has(student.id)) next.delete(student.id);
            else next.add(student.id);
            return next;
        });
    }

    /** Tick every student the filters match - across all pages, not only this one. */
    async function toggleAll() {
        if (allSelected) {
            setSelected(new Set());
            return;
        }
        const ids = allIds ?? (await s.fetchAllIds());
        setAllIds(ids);
        setSelected(new Set(ids));
    }

    /** Run one promotion call, report what happened, and re-read the roster. */
    async function act(
        call: () => Promise<PromotionResult>,
        verb: string,
        failure: string,
    ): Promise<void> {
        setActing(true);
        setError(null);
        try {
            const result = await call();
            toast.push(result.done > 0 ? "success" : "error", resultMessage(verb, result));
            setSelected(new Set());
            setAllIds(null);
            await s.refresh();
        } catch (cause) {
            const message = errorMessage(cause, failure);
            setError(message);
            toast.push("error", message);
        } finally {
            setActing(false);
        }
    }

    const ids = () => [...selected];

    // De-promote moves a student one class down: it needs a class below, and a student
    // who is a new admission or a promoted one (the server checks again).
    const lowerClass = lowerClassOf(catalog.classes, className);
    const visibleSelected = (s.students ?? []).filter((row) => selected.has(row.id));
    const offPageSelected = selected.size > visibleSelected.length;
    const canUndo = visibleSelected.some((row) => doneKindOf(row) !== null);
    const retainUndo = undoLabel(visibleSelected, "retained", "Retain") !== "Retain";
    const moveUndo = undoLabel(visibleSelected, "moved", "De-promote") !== "De-promote";
    const canDepromote =
        offPageSelected ||
        visibleSelected.some(
            (row) =>
                (row.promotionStatus ?? "NEW_ADMISSION") === "NEW_ADMISSION" ||
                row.promotionStatus === "PROMOTED",
        );

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

            {error && <p className="text-sm text-red-500">{error}</p>}

            {canPromote && (
                <PromoteBar
                    className={className}
                    classes={catalog.classes}
                    selectedCount={selected.size}
                    busy={acting}
                    sectionNames={catalog.sectionNames}
                    onPromote={(target?: CatalogClass, targetSection?: string) =>
                        act(
                            () => promoteStudents(ids(), target?.id, targetSection),
                            "promoted",
                            "Could not promote the students.",
                        )
                    }
                    onComplete={() =>
                        act(
                            () => completeStudents(ids()),
                            "marked completed",
                            "Could not mark the students completed.",
                        )
                    }
                    onRetain={() =>
                        act(
                            () => retainStudents(ids()),
                            "retained",
                            "Could not retain the students.",
                        )
                    }
                    blockedReason={blockedReason}
                    canUndo={canUndo}
                    retainUndo={retainUndo}
                    moveUndo={moveUndo}
                    onPreviewUndo={() => previewUndo(ids())}
                    onUndo={() =>
                        act(() => undoStudents(ids(), true), "restored", "Could not undo.")
                    }
                    lowerClass={lowerClass}
                    canDepromote={canDepromote}
                    onDepromote={(section) =>
                        act(
                            () => demoteStudents(ids(), section),
                            "moved down",
                            "Could not move the students down.",
                        )
                    }
                />
            )}

            <StudentTable
                rows={s.students}
                totalItems={s.totalItems}
                page={s.page}
                pageSize={s.pageSize}
                onPageChange={s.setPage}
                onView={setProfile}
                layout="section"
                selection={
                    canPromote
                        ? {
                              selected,
                              onToggle: toggleOne,
                              onToggleAll: () => void toggleAll(),
                              allSelected,
                              totalMatching: s.totalItems,
                          }
                        : undefined
                }
            />

            <StudentProfileSheet student={profile} onClose={() => setProfile(null)} />
        </div>
    );
}
