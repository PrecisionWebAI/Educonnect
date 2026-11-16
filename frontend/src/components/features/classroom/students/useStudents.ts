"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    addStudentGuardian,
    createStudent,
    deactivateStudent,
    getStudentsPage,
    reactivateStudent,
    updateStudent,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { useClassCatalog } from "@/hooks/use-class-catalog";
import type { Student } from "@/types";

// All student data logic in one hook — pages stay thin.
//
// Two things changed in Phase 1, and both are the point of this file:
//
//   * every button now **writes to the database** (create, edit, deactivate,
//     reactivate) and the list is re-read afterwards; the old cache-only writes made
//     a new child vanish on reload;
//   * search, the two filters and the paging run **on the server** - the browser used
//     to filter the hundred rows it had been given, so student 101 was invisible.
//
// The hook still serves two hosts: the school-wide directory (no scope) and the
// Students view inside one class-section, which passes `className` + `section` so the
// list only ever shows that room's children (resolved to the room's id through the
// class catalog, because the API takes an id).

export interface StudentScope {
    /** Only students of this class ("Class 6"). Omit for the whole school. */
    className?: string;
    /** Only students of this section letter ("B"). */
    section?: string;
}

export interface StudentFormValues {
    name: string;
    admissionNo: string;
    className: string;
    section: string;
    gender: Student["gender"];
    guardian: string;
    phone: string;
    email: string;
}

export const EMPTY_FORM: StudentFormValues = {
    name: "",
    admissionNo: "",
    // Filled from the class catalogue when the modal opens - the form must not carry
    // a class name of its own.
    className: "",
    section: "",
    gender: "Male",
    guardian: "",
    phone: "",
    email: "",
};

/** How long the search box waits before asking the server. */
const SEARCH_DEBOUNCE_MS = 300;

/** One page of the directory, the way the table draws it. */
const DEFAULT_PAGE_SIZE = 10;

export function useStudents(scope: StudentScope = {}) {
    const queryClient = useQueryClient();
    const catalog = useClassCatalog();

    const [query, setQueryState] = useState("");
    const [debouncedQuery, setDebouncedQuery] = useState("");
    useEffect(() => {
        const timer = setTimeout(() => setDebouncedQuery(query), SEARCH_DEBOUNCE_MS);
        return () => clearTimeout(timer);
    }, [query]);

    const [classFilter, setClassFilterState] = useState("all");
    const [statusFilter, setStatusFilterState] = useState("all");
    const [page, setPageState] = useState(1);
    const [pageSize, setPageSizeState] = useState(DEFAULT_PAGE_SIZE);
    const [busy, setBusy] = useState(false);

    // The class-section this page is about, resolved to the room's id.
    const scopedClassroomId = useMemo(() => {
        if (!scope.className || !scope.section) return undefined;
        return catalog.sectionsOf(scope.className).find((section) => section.name === scope.section)
            ?.classroomId;
    }, [catalog, scope.className, scope.section]);

    const filterClassId = useMemo(() => {
        if (classFilter === "all") return undefined;
        return catalog.classes.find((item) => item.name === classFilter)?.id;
    }, [catalog, classFilter]);

    const pageQuery = useMemo(
        () => ({
            q: debouncedQuery,
            classroomId: scopedClassroomId,
            classId: filterClassId,
            status:
                statusFilter === "Active" || statusFilter === "Inactive"
                    ? (statusFilter as "Active" | "Inactive")
                    : undefined,
            skip: (page - 1) * pageSize,
            limit: pageSize,
        }),
        [debouncedQuery, scopedClassroomId, filterClassId, statusFilter, page, pageSize],
    );

    const studentsQuery = useApiQuery(["students", "page", pageQuery], () =>
        getStudentsPage(pageQuery),
    );

    const students = studentsQuery.data?.items ?? null;
    const totalItems = studentsQuery.data?.total ?? students?.length ?? 0;

    /** Every write ends here: the page is re-read, so the screen shows the database. */
    const refresh = useCallback(
        () => queryClient.invalidateQueries({ queryKey: ["students"] }),
        [queryClient],
    );

    // A narrower filter makes page 4 empty, so every filter goes back to page 1.
    const setQuery = useCallback((value: string) => {
        setQueryState(value);
        setPageState(1);
    }, []);
    const setClassFilter = useCallback((value: string) => {
        setClassFilterState(value);
        setPageState(1);
    }, []);
    const setStatusFilter = useCallback((value: string) => {
        setStatusFilterState(value);
        setPageState(1);
    }, []);
    const setPageSize = useCallback((value: number) => {
        setPageSizeState(value);
        setPageState(1);
    }, []);

    /** The room the form's class + section means, as the id the API wants. */
    const classroomIdFor = useCallback(
        (className: string, section: string): string | null =>
            catalog.sectionsOf(className).find((item) => item.name === section)?.classroomId ??
            null,
        [catalog],
    );

    /**
     * Save the modal: create when there is no id, edit when there is.
     *
     * The guardian the form collects is a **person of their own**, so a new child gets
     * the guardian link in the same action - a directory that quietly dropped the
     * parent's name would look successful and lose the contact.
     */
    const save = useCallback(
        async (values: StudentFormValues, editingId?: string) => {
            const classroomId = classroomIdFor(values.className, values.section);
            setBusy(true);
            try {
                if (editingId) {
                    await updateStudent(editingId, {
                        fullName: values.name.trim(),
                        gender: values.gender,
                        classroomId,
                    });
                } else {
                    const created = await createStudent({
                        fullName: values.name.trim(),
                        gender: values.gender,
                        classroomId,
                    });
                    if (values.guardian.trim() && values.phone.trim()) {
                        await addStudentGuardian(created.id, {
                            name: values.guardian.trim(),
                            phone: values.phone.trim(),
                            email: values.email.trim() || undefined,
                            relation: "guardian",
                            is_primary: true,
                        });
                    }
                }
                await refresh();
            } finally {
                setBusy(false);
            }
        },
        [classroomIdFor, refresh],
    );

    /** "Mark as left" / "Bring back" - the lifecycle routes, never a cache flip. */
    const setStatus = useCallback(
        async (student: Student) => {
            setBusy(true);
            try {
                if (student.status === "Active") await deactivateStudent(student.id);
                else await reactivateStudent(student.id);
                await refresh();
            } finally {
                setBusy(false);
            }
        },
        [refresh],
    );

    function toForm(student: Student): StudentFormValues {
        return {
            name: student.name,
            admissionNo: student.admissionNo,
            className: student.className,
            section: student.section,
            gender: student.gender,
            guardian: student.guardian,
            phone: student.phone,
            email: student.email,
        };
    }

    return {
        students,
        loading: students === null,
        busy,
        query,
        setQuery,
        classFilter,
        setClassFilter,
        statusFilter,
        setStatusFilter,
        page,
        setPage: setPageState,
        pageSize,
        setPageSize,
        totalItems,
        save,
        setStatus,
        toForm,
    };
}
