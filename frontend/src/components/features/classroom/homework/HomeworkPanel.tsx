"use client";

import { useMemo, useState } from "react";
import { Badge, Input, Spinner, Table, Tabs } from "@/components/ui";
import { useAuth } from "@/providers/auth-context";
import { ACADEMIC_STAFF_ROLES, hasAnyRole } from "@/lib/auth/rbac";
import { boardCounts, progressText } from "@/lib/homework/view";
import { useHomework, type HomeworkTab } from "./useHomework";
import AssignHomework from "./AssignHomework";
import ClassDiary from "./ClassDiary";
import SubmissionsReview from "./SubmissionsReview";
import WriteDailyLog from "./WriteDailyLog";

// Homework & diary **inside one class-section** (Phase 9).
//
// Three tabs, all reading this section's own rows from the server:
//
//   Assign Homework       - the form, plus what is already out (with "2/4 in");
//   Submissions & Review  - one line per child per assignment, gradeable, late flagged;
//   Class Diary           - the lines written, and the small form that writes one.

const ALL_TABS: HomeworkTab[] = ["Assign Homework", "Submissions & Review", "Class Diary"];

export default function HomeworkPanel({
    sectionId,
    classroomId,
    className,
    section,
    subjects,
    teachers,
    defaultTeacherId,
}: {
    sectionId: string;
    /** The class-section's class - the timetable read (for the log form) needs it. */
    classroomId: string;
    className: string;
    section: string;
    /** The subjects this class-section studies. */
    subjects: { id: string; name: string }[];
    /** Who can be credited with an assignment or a log line. */
    teachers: { employeeId: string; name: string }[];
    /** The section's class teacher, preselected when there is one. */
    defaultTeacherId: string | null;
}) {
    const { user } = useAuth();
    const canAssign = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);
    const h = useHomework({ sectionId, className, section });
    const [tab, setTab] = useState<HomeworkTab>(
        canAssign ? "Assign Homework" : "Submissions & Review",
    );

    const allowedTabs = useMemo(
        () => (canAssign ? ALL_TABS : ALL_TABS.filter((t) => t !== "Assign Homework")),
        [canAssign],
    );
    const activeTab = allowedTabs.includes(tab) ? tab : allowedTabs[0];
    const counts = boardCounts(h.submissions);

    if (h.loading) return <Spinner />;

    return (
        <div className="space-y-4">
            <div className="stat-tiles">
                <div className="stat-tile">
                    <b>{h.homeworks.length}</b>
                    <span>Assigned</span>
                </div>
                <div className="stat-tile">
                    <b>
                        {counts.handedIn}/{counts.handedIn + counts.pending}
                    </b>
                    <span>Handed in</span>
                </div>
                <div className="stat-tile">
                    <b>{counts.graded}</b>
                    <span>Graded</span>
                </div>
                <div className="stat-tile">
                    <b>{h.diary.length}</b>
                    <span>Diary lines</span>
                </div>
            </div>

            <Tabs
                tabs={allowedTabs}
                active={activeTab}
                onChange={(t) => setTab(t as HomeworkTab)}
            />

            {activeTab === "Assign Homework" && canAssign && (
                <div className="space-y-4">
                    <AssignHomework
                        sectionId={sectionId}
                        sectionLabel={`${className}-${section}`}
                        subjects={subjects}
                        teachers={teachers}
                        defaultTeacherId={defaultTeacherId}
                        onAssigned={h.refresh}
                    />
                    <AssignmentBoard rows={h.filteredHomeworks} />
                </div>
            )}

            {(activeTab === "Submissions & Review" || activeTab === "Class Diary") && (
                <div className="toolbar">
                    <div className="toolbar-search">
                        <Input
                            placeholder={
                                activeTab === "Class Diary"
                                    ? "Search the diary by what was done or the subject…"
                                    : "Search by student or homework…"
                            }
                            value={h.query}
                            onChange={(e) => h.setQuery(e.target.value)}
                        />
                    </div>
                </div>
            )}

            {activeTab === "Submissions & Review" && (
                <SubmissionsReview rows={h.filteredSubmissions} onGraded={h.refresh} />
            )}

            {activeTab === "Class Diary" && (
                <div className="space-y-4">
                    {canAssign && (
                        <WriteDailyLog
                            sectionId={sectionId}
                            classroomId={classroomId}
                            subjects={subjects}
                            teacherId={defaultTeacherId ?? teachers[0]?.employeeId ?? null}
                            onSaved={h.refresh}
                        />
                    )}
                    <ClassDiary rows={h.filteredDiary} />
                </div>
            )}
        </div>
    );
}

/** What is already out for this section, with the "2/4 in" the board now counts. */
function AssignmentBoard({ rows }: { rows: ReturnType<typeof useHomework>["homeworks"] }) {
    return (
        <Table
            columns={[
                {
                    key: "title",
                    header: "Assignment",
                    render: (item) => (
                        <div className="min-w-0">
                            <p className="truncate font-medium">{item.title}</p>
                            <p className="text-muted-foreground truncate text-xs">
                                {item.subject} · set by {item.assignedBy ?? "—"}
                            </p>
                        </div>
                    ),
                },
                {
                    key: "due",
                    header: "Due",
                    render: (item) => (
                        <div className="flex items-center gap-2">
                            <span className="text-sm">{item.dueDate}</span>
                            <Badge tone={item.due === "Overdue" ? "red" : "muted"}>
                                {item.due}
                            </Badge>
                        </div>
                    ),
                },
                {
                    key: "in",
                    header: "Handed in",
                    align: "right",
                    render: (item) => (
                        <span className="text-sm tabular-nums">{progressText(item)}</span>
                    ),
                },
            ]}
            rows={rows}
            rowKey={(item) => item.id}
            empty="Nothing has been assigned to this class-section yet."
        />
    );
}
