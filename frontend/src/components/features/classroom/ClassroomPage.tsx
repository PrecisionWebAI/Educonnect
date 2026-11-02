"use client";
import { PageHeader, Spinner } from "@/components/ui";
import RoleGuard from "@/components/auth/RoleGuard";
import ClassroomCards from "./ClassroomCards";
import TeacherClassroom from "./TeacherClassroom";
import { useClassroomOverview } from "./useClassroomOverview";

// Operations ▸ Classroom.
//
// Two views live here, picked by role:
//   * principal and above — the school-wide grid: a heading per class with a card
//     per class-section, each carrying its real attendance / fees / syllabus /
//     marks figures.
//   * a teacher — their own classes and lesson plan (unchanged).

/** Principal-and-above: every class the school uses, one card per class-section. */
function SchoolClassroom() {
    const { groups, loading } = useClassroomOverview();

    return (
        <div>
            <PageHeader
                title="Classroom"
                subtitle="Every class at a glance — students, attendance, fees and progress."
            />
            {loading ? <Spinner /> : <ClassroomCards groups={groups} />}
        </div>
    );
}

export default function ClassroomPage() {
    return (
        <RoleGuard
            allowedRoles={[
                "SYSTEM_ADMIN",
                "SCHOOL_ADMIN",
                "PRINCIPAL",
                "VICE_PRINCIPAL",
                "HOD",
            ]}
            fallback={<TeacherClassroom />}
        >
            <SchoolClassroom />
        </RoleGuard>
    );
}

