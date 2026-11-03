"use client";

import { useMemo, useState } from "react";
import { Input, Spinner, Tabs } from "@/components/ui";
import { useAuth } from "@/providers/auth-context";
import { ACADEMIC_STAFF_ROLES, hasAnyRole } from "@/lib/auth/rbac";
import { useHomework, type HomeworkTab } from "./useHomework";
import AssignHomework from "./AssignHomework";
import SubmissionsReview from "./SubmissionsReview";
import ClassDiary from "./ClassDiary";

// Homework & diary **inside one class-section**.
//
// The same three panels the school-wide screen used, narrowed to the section the
// page is showing: assignments from that section's own endpoint, submissions only
// from its students, and the diary only for that class-section.

const ALL_TABS: HomeworkTab[] = ["Assign Homework", "Submissions & Review", "Class Diary"];

export default function HomeworkPanel({
    sectionId,
    className,
    section,
    subjects,
    teachers,
    defaultTeacherId,
}: {
    sectionId: string;
    className: string;
    section: string;
    /** The subjects this school offers - what an assignment can be set for. */
    subjects: { id: string; name: string }[];
    /** Who can be credited with an assignment. */
    teachers: { employeeId: string; name: string }[];
    /** The section's class teacher, preselected when there is one. */
    defaultTeacherId: string | null;
}) {
    const { user } = useAuth();
    const canAssign = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);
    const h = useHomework({ sectionId, className, section });
    const [tab, setTab] = useState<HomeworkTab>(canAssign ? "Assign Homework" : "Submissions & Review");

    const allowedTabs = useMemo(
        () => (canAssign ? ALL_TABS : ALL_TABS.filter((t) => t !== "Assign Homework")),
        [canAssign],
    );
    const activeTab = allowedTabs.includes(tab) ? tab : allowedTabs[0];

    if (h.loading) return <Spinner />;

    return (
        <div className="space-y-4">
            <div className="stat-tiles">
                <div className="stat-tile">
                    <b>{h.homeworks.length}</b>
                    <span>Active Tasks</span>
                </div>
                <div className="stat-tile">
                    <b>{h.submittedCount}</b>
                    <span>Submitted</span>
                </div>
                <div className="stat-tile">
                    <b>{h.pendingCount}</b>
                    <span>Pending</span>
                </div>
                <div className="stat-tile">
                    <b>{h.diary.length}</b>
                    <span>Diary Days</span>
                </div>
            </div>

            <Tabs tabs={allowedTabs} active={activeTab} onChange={(t) => setTab(t as HomeworkTab)} />

            {activeTab === "Assign Homework" && canAssign && (
                <AssignHomework
                    sectionId={sectionId}
                    sectionLabel={`${className}-${section}`}
                    subjects={subjects}
                    teachers={teachers}
                    defaultTeacherId={defaultTeacherId}
                />
            )}

            {(activeTab === "Submissions & Review" || activeTab === "Class Diary") && (
                <div className="toolbar">
                    <div className="toolbar-search">
                        <Input
                            placeholder={
                                activeTab === "Class Diary"
                                    ? "Search diary by topic or subject…"
                                    : "Search student or homework…"
                            }
                            value={h.query}
                            onChange={(e) => h.setQuery(e.target.value)}
                        />
                    </div>
                </div>
            )}

            {activeTab === "Submissions & Review" && (
                <SubmissionsReview rows={h.filteredSubmissions} />
            )}
            {activeTab === "Class Diary" && (
                <ClassDiary
                    rows={h.diary.filter(
                        (d) =>
                            !h.query ||
                            d.topic.toLowerCase().includes(h.query.toLowerCase()) ||
                            d.subject.toLowerCase().includes(h.query.toLowerCase()),
                    )}
                />
            )}
        </div>
    );
}
