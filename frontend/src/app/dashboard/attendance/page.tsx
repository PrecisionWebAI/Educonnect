"use client";

import RoleGuard from "@/components/auth/RoleGuard";
import AttendancePage from "@/components/features/classroom/attendance/AttendancePage";

// Marking attendance now lives **inside the Classroom**: open a class-section and
// its Attendance tab takes that section's register (saved for real).
//
// This route keeps only the personal view - a student's or guardian's own history
// - so staff have no school-wide attendance screen outside the Classroom.
export default function Page() {
    return (
        <RoleGuard allowedRoles={["STUDENT", "GUARDIAN"]}>
            <AttendancePage />
        </RoleGuard>
    );
}

