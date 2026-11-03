"use client";

import RoleGuard from "@/components/auth/RoleGuard";
import TimetablePage from "@/components/features/timetable/TimetablePage";

// Timetabling now lives **inside the Classroom**: open a class-section and its
// Timetable tab edits that room's week for real.
//
// This route keeps only the personal view — a student or guardian looking at
// their own class's week — so staff have no second, read-only timetable screen.
export default function Page() {
    return (
        <RoleGuard allowedRoles={["STUDENT", "GUARDIAN"]}>
            <TimetablePage />
        </RoleGuard>
    );
}
