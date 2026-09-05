"use client";
import { useMemo, useState } from "react";
import { PageHeader, Tabs, Input, Spinner } from "@/components/ui";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, isStudent, isParent, ACADEMIC_STAFF_ROLES } from "@/lib/auth/rbac";
import { useHomework, type HomeworkTab } from "./useHomework";
import AssignHomework from "./AssignHomework";
import SubmissionsReview from "./SubmissionsReview";
import ClassDiary from "./ClassDiary";

const ALL_TABS: HomeworkTab[] = ["Assign Homework", "Submissions & Review", "Class Diary"];

export default function HomeworkPage() {
    const { user } = useAuth();
    const isStudentUser = isStudent(user?.roles);
    const isParentUser = isParent(user?.roles);
    const canAssign = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);

    const allowedTabs = useMemo(() => {
        if (isStudentUser || isParentUser) {
            return ["Submissions & Review" as HomeworkTab, "Class Diary" as HomeworkTab];
        }
        return ALL_TABS;
    }, [isStudentUser, isParentUser]);

    const [tab, setTab] = useState<HomeworkTab>(() =>
        canAssign ? "Assign Homework" : "Submissions & Review",
    );
    const activeTab = allowedTabs.includes(tab) ? tab : allowedTabs[0];

    const h = useHomework();

    const title = isStudentUser
        ? "My Homework & Class Diary"
        : isParentUser
          ? "Child Homework & Class Diary"
          : "Homework & Class Diary";

    const subtitle =
        isStudentUser || isParentUser
            ? "Track assigned tasks, upload homework submissions, and view daily class diaries."
            : "Assign homework, review submissions and manage the class diary.";

    return (
        <div>
            <PageHeader title={title} subtitle={subtitle} />

            {h.loading ? (
                <Spinner />
            ) : (
                <>
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

                    <Tabs
                        tabs={allowedTabs}
                        active={activeTab}
                        onChange={(t) => setTab(t as HomeworkTab)}
                    />

                    {activeTab === "Assign Homework" && canAssign && <AssignHomework />}

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
                </>
            )}
        </div>
    );
}
