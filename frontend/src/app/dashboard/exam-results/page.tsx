"use client";

import { useState } from "react";
import RoleGuard from "@/components/auth/RoleGuard";
import ExamResultPanel from "@/components/features/classroom/exam-plan/ExamResultPanel";
import FamilyExamsView from "@/components/features/classroom/exam-plan/FamilyExamsView";
import AcademicYearRequiredBanner from "@/components/layout/AcademicYearRequiredBanner";
import { PageHeader, Tabs } from "@/components/ui";
import { isStudent } from "@/lib/auth/rbac";
import { useAuth } from "@/providers/auth-context";

// A student's or guardian's own exams.
//
//   Upcoming - the class tests and the published date sheets (with syllabus) of their own
//              children's sections;
//   Results  - the published results, subject-wise so far and overall.
//
// Staff read the same things inside a class-section (Classroom -> Exams); this route is the
// personal view. It asks the server for **no section**, so every answer is the caller's own
// children only - and only what the teachers have published.
export default function Page() {
    return (
        <RoleGuard allowedRoles={["STUDENT", "GUARDIAN"]}>
            <Exams />
        </RoleGuard>
    );
}

const TABS = ["Upcoming", "Results"] as const;

function Exams() {
    const { user } = useAuth();
    const own = isStudent(user?.roles);
    const [tab, setTab] = useState<(typeof TABS)[number]>("Upcoming");
    return (
        <div className="page">
            <PageHeader
                title={own ? "My Exams" : "Exams"}
                subtitle={
                    own
                        ? "Your class tests, date sheets and results, once your teachers have published them"
                        : "Your child's class tests, date sheets and results, once the teachers have published them"
                }
            />
            <AcademicYearRequiredBanner className="mb-4" />
            <div className="space-y-4">
                <Tabs
                    tabs={[...TABS]}
                    active={tab}
                    onChange={(next) => setTab(next as typeof tab)}
                />
                {tab === "Upcoming" ? <FamilyExamsView /> : <ExamResultPanel classroomId={null} />}
            </div>
        </div>
    );
}
