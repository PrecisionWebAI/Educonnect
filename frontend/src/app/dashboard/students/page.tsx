"use client";

import RoleGuard from "@/components/auth/RoleGuard";
import StudentsPage from "@/components/features/classroom/students/StudentsPage";

// The student directory now lives **inside the Classroom**: open a class-section
// and its Students tab opens on that class by default (see
// `features/classroom/students/StudentsPanel`).
//
// This route keeps only the personal view - a student or guardian looking at their
// own record - so staff have no school-wide student screen outside the Classroom.
export default function Page() {
    return (
        <RoleGuard allowedRoles={["STUDENT", "GUARDIAN"]}>
            <StudentsPage />
        </RoleGuard>
    );
}

