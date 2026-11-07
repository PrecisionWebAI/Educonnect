"use client";

import { useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getStudents } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { Student } from "@/types";

// All student data logic in one hook — pages stay thin.
//
// The same hook serves two hosts: the school-wide directory (no scope) and the
// Students view **inside one class-section**, which passes `className` + `section`
// so the list only ever shows that section's students.

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
    // Filled from the class catalogue (`useClassCatalog`) when the modal opens -
    // the form must not carry a class name of its own.
    className: "",
    section: "",
    gender: "Male",
    guardian: "",
    phone: "",
    email: "",
};

export function useStudents(scope: StudentScope = {}) {
    const queryClient = useQueryClient();
    const studentsQuery = useApiQuery(["students"], () => getStudents());
    const students = studentsQuery.data ?? null;
    const [query, setQuery] = useState("");
    const [classFilter, setClassFilter] = useState("all");
    const [statusFilter, setStatusFilter] = useState("all");
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(5);

    const handleQueryChange: Dispatch<SetStateAction<string>> = (action) => {
        setQuery(action);
        setPage(1);
    };

    const handleClassFilterChange: Dispatch<SetStateAction<string>> = (action) => {
        setClassFilter(action);
        setPage(1);
    };

    const handleStatusFilterChange: Dispatch<SetStateAction<string>> = (action) => {
        setStatusFilter(action);
        setPage(1);
    };

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        return (students ?? []).filter((s) => {
            // The section scope first: inside a class-section the panel must never
            // show another class's student, whatever the filters say.
            if (scope.className && s.className !== scope.className) return false;
            if (scope.section && s.section !== scope.section) return false;
            if (q && !`${s.name} ${s.admissionNo} ${s.guardian}`.toLowerCase().includes(q))
                return false;
            if (classFilter !== "all" && s.className !== classFilter) return false;
            if (statusFilter !== "all" && s.status !== statusFilter) return false;
            return true;
        });
    }, [students, query, classFilter, statusFilter, scope.className, scope.section]);

    const paginated = useMemo(() => {
        const start = (page - 1) * pageSize;
        return filtered.slice(start, start + pageSize);
    }, [filtered, page, pageSize]);

    function toForm(s: Student): StudentFormValues {
        return {
            name: s.name,
            admissionNo: s.admissionNo,
            className: s.className,
            section: s.section,
            gender: s.gender,
            guardian: s.guardian,
            phone: s.phone,
            email: s.email,
        };
    }

    function addStudent(values: StudentFormValues) {
        queryClient.setQueryData<Student[]>(["students"], (prev) => [
            { id: crypto.randomUUID(), ...values, status: "Active" },
            ...(prev ?? []),
        ]);
    }

    function updateStudent(id: string, values: StudentFormValues) {
        queryClient.setQueryData<Student[]>(["students"], (prev) =>
            (prev ?? []).map((s) => (s.id === id ? { ...s, ...values } : s)),
        );
    }

    function toggleStatus(s: Student) {
        queryClient.setQueryData<Student[]>(["students"], (prev) =>
            (prev ?? []).map((x) =>
                x.id === s.id ? { ...x, status: x.status === "Active" ? "Inactive" : "Active" } : x,
            ),
        );
    }

    return {
        students,
        filtered,
        paginated,
        query,
        setQuery: handleQueryChange,
        classFilter,
        setClassFilter: handleClassFilterChange,
        statusFilter,
        setStatusFilter: handleStatusFilterChange,
        page,
        setPage,
        pageSize,
        setPageSize,
        totalItems: filtered.length,
        toForm,
        addStudent,
        updateStudent,
        toggleStatus,
    };
}
