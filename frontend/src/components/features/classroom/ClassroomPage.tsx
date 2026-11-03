"use client";
import { useState } from "react";
import { PageHeader, Spinner, Tabs } from "@/components/ui";
import RoleGuard from "@/components/auth/RoleGuard";
import ClassroomCards from "./ClassroomCards";
import TeacherClassroom from "./TeacherClassroom";
import AttendanceInsightsPanel from "./attendance/AttendanceInsightsPanel";
import DisputesPanel from "./academics/DisputesPanel";
import ResultsPanel from "./academics/ResultsPanel";
import ClassMatrixPanel from "./students/ClassMatrixPanel";
import { useClassroomOverview } from "./useClassroomOverview";

// Operations ▸ Classroom.
//
// Two views live here, picked by role:
//   * principal and above — the school-wide grid (a card per class-section), plus
//     the two school-wide views that are about every class at once: the class
//     matrix and attendance insights. Opening a card shows that section's
//     Students and Attendance.
//   * a teacher — their own classes and lesson plan (unchanged).

/** The school-wide views that are about every class at once. */
type GridTab =
    | "Classrooms"
    | "Class matrix"
    | "Attendance insights"
    | "Results"
    | "Marks dispute";
const GRID_TABS: GridTab[] = [
    "Classrooms",
    "Class matrix",
    "Attendance insights",
    "Results",
    "Marks dispute",
];

/** Principal-and-above: every class the school uses, one card per class-section. */
function SchoolClassroom() {
    const { groups, loading } = useClassroomOverview();
    const [tab, setTab] = useState<GridTab>("Classrooms");

    return (
        <div>
            <PageHeader
                title="Classroom"
                subtitle="Every class at a glance — open a class-section for its students, attendance, marks and homework."
            />

            <Tabs
                tabs={[...GRID_TABS]}
                active={tab}
                onChange={(next) => setTab(next as GridTab)}
            />

            <div className="mt-4">
                {tab === "Classrooms" ? (
                    loading ? (
                        <Spinner />
                    ) : (
                        <ClassroomCards groups={groups} />
                    )
                ) : tab === "Class matrix" ? (
                    <ClassMatrixPanel />
                ) : tab === "Attendance insights" ? (
                    <AttendanceInsightsPanel />
                ) : tab === "Results" ? (
                    <ResultsPanel />
                ) : (
                    <DisputesPanel />
                )}
            </div>
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

