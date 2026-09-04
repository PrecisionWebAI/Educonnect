"use client";

import { useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { getStudents } from "@/services";
import type { Student } from "@/types";

// All student data logic in one hook — pages stay thin.

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
    className: "10",
    section: "A",
    gender: "Male",
    guardian: "",
    phone: "",
    email: "",
};

export function useStudents() {
    const [students, setStudents] = useState<Student[] | null>(null);
    const [query, setQuery] = useState("");
    const [classFilter, setClassFilter] = useState("all");
    const [statusFilter, setStatusFilter] = useState("all");
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(5);

    useEffect(() => {
        void getStudents().then(setStudents);
    }, []);

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

    const classes = useMemo(
        () => Array.from(new Set((students ?? []).map((s) => s.className))).sort(),
        [students],
    );

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        return (students ?? []).filter((s) => {
            if (q && !`${s.name} ${s.admissionNo} ${s.guardian}`.toLowerCase().includes(q))
                return false;
            if (classFilter !== "all" && s.className !== classFilter) return false;
            if (statusFilter !== "all" && s.status !== statusFilter) return false;
            return true;
        });
    }, [students, query, classFilter, statusFilter]);

    const paginated = useMemo(() => {
        const start = (page - 1) * pageSize;
        return filtered.slice(start, start + pageSize);
    }, [filtered, page, pageSize]);

    function nextAdmissionNo() {
        const nums = (students ?? [])
            .map((s) => Number.parseInt(s.admissionNo.split("-").pop() ?? "0", 10))
            .filter((n) => !Number.isNaN(n));
        return `EV-2026-${String((nums.length ? Math.max(...nums) : 0) + 1).padStart(3, "0")}`;
    }

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
        setStudents((prev) => [{ id: Date.now(), ...values, status: "Active" }, ...(prev ?? [])]);
    }

    function updateStudent(id: number, values: StudentFormValues) {
        setStudents((prev) => (prev ?? []).map((s) => (s.id === id ? { ...s, ...values } : s)));
    }

    function toggleStatus(s: Student) {
        setStudents((prev) =>
            (prev ?? []).map((x) =>
                x.id === s.id ? { ...x, status: x.status === "Active" ? "Inactive" : "Active" } : x,
            ),
        );
    }

    return {
        students,
        filtered,
        paginated,
        classes,
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
        nextAdmissionNo,
        toForm,
        addStudent,
        updateStudent,
        toggleStatus,
    };
}
