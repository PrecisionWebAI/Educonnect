"use client";

import { useState } from "react";
import { EmptyState, Spinner, Tabs } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { hasResults } from "@/lib/exams/results";
import ResultClassView from "./ResultClassView";
import StudentResultDetail from "./StudentResultDetail";
import { useResultOverview } from "./useExamPlan";

// The **Overall Result** tab: Class Test Result and School Exam Result, each on its own and
// never mixed, for the academic year on screen.
//
//   * With a `classroomId` (a section's page) it is the **class view** - for that section's
//     teachers and for leadership, who open any section from the Classroom list;
//   * without one (a student's or guardian's own page) it is **their own children** only,
//     only for published tests, with no class figures at all.
//
// The server decides who may see what (`GET /exams/results/overview`): a section that is not
// the caller's is a `404`. This screen only draws the answer, in the school's display mode.

const TABS = ["Class Test Result", "School Exam Result"] as const;

export default function ExamResultPanel({ classroomId = null }: { classroomId?: string | null }) {
    const [tab, setTab] = useState<(typeof TABS)[number]>("Class Test Result");
    const kind = tab === "Class Test Result" ? "class_test" : "school_exam";
    const query = useResultOverview(kind, classroomId);

    return (
        <div className="space-y-4">
            <Tabs tabs={[...TABS]} active={tab} onChange={(next) => setTab(next as typeof tab)} />

            {query.isPending ? (
                <Spinner />
            ) : query.isError ? (
                <p className="text-sm text-red-500" role="alert">
                    {errorMessage(query.error, "Could not read the results.")}
                </p>
            ) : !query.data ? null : query.data.view === "section" ? (
                <ResultClassView data={query.data} />
            ) : query.data.students.length === 0 ? (
                <EmptyState
                    icon="🎓"
                    title="No child is linked to this login"
                    body="Results appear here once a student is linked to your account."
                />
            ) : !hasResults(query.data) ? (
                <EmptyState
                    icon="📄"
                    title={
                        kind === "class_test"
                            ? "No class test result yet"
                            : "No school exam result yet"
                    }
                    body="Results appear here once the teacher has published the marks."
                />
            ) : (
                <div className="space-y-6">
                    {query.data.students.map((student) => (
                        <section key={student.studentId} className="space-y-3">
                            <div>
                                <h3 className="text-base font-semibold tracking-tight">
                                    {student.name}
                                </h3>
                                <p className="text-muted-foreground text-xs">
                                    {student.section || "—"}
                                </p>
                            </div>
                            <StudentResultDetail
                                student={student}
                                tests={query.data.tests}
                                mode={query.data.displayMode}
                            />
                        </section>
                    ))}
                </div>
            )}
        </div>
    );
}
