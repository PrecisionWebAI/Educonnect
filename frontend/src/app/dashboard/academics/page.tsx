"use client";

import RoleGuard from "@/components/auth/RoleGuard";
import AcademicsPage from "@/components/features/classroom/academics/AcademicsPage";

// Marks now live **inside the Classroom**: open a class-section and its Academics
// tab shows that section's students' marks (entry + gradebook), saved for real.
//
// This route keeps only the personal view - a student's or guardian's own results.
export default function Page() {
    return (
        <RoleGuard allowedRoles={["STUDENT", "GUARDIAN"]}>
            <AcademicsPage />
        </RoleGuard>
    );
}

