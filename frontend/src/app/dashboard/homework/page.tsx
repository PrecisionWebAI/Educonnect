"use client";

import RoleGuard from "@/components/auth/RoleGuard";
import HomeworkPage from "@/components/features/classroom/homework/HomeworkPage";

// Homework & the class diary now live **inside the Classroom**: open a
// class-section and its Homework tab shows that section's tasks, submissions and
// diary.
//
// This route keeps only the personal view - a student's or guardian's own tasks.
export default function Page() {
    return (
        <RoleGuard allowedRoles={["STUDENT", "GUARDIAN"]}>
            <HomeworkPage />
        </RoleGuard>
    );
}

