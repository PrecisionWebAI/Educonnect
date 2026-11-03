"use client";
import { useState } from "react";
import { PageHeader, Tabs, Input, Spinner } from "@/components/ui";
import { useAuth } from "@/providers/auth-context";
import { isStudent, isParent } from "@/lib/auth/rbac";
import { useHomework, type HomeworkTab } from "./useHomework";
import SubmissionsReview from "./SubmissionsReview";
import ClassDiary from "./ClassDiary";

// What a student (or their guardian) sees: the homework set for their class and the
// class diary. **Assigning** homework happens inside the Classroom, on the
// class-section it is for, so this page has no assign tab.

const TABS: HomeworkTab[] = ["Submissions & Review", "Class Diary"];

export default function HomeworkPage() {
    const { user } = useAuth();
    const isStudentUser = isStudent(user?.roles);
    const isParentUser = isParent(user?.roles);

    const [tab, setTab] = useState<HomeworkTab>("Submissions & Review");
    const activeTab = TABS.includes(tab) ? tab : TABS[0];

    const h = useHomework();

    const title = isStudentUser
        ? "My Homework & Class Diary"
        : isParentUser
          ? "Child Homework & Class Diary"
          : "Homework & Class Diary";

    const subtitle =
        "Track assigned tasks, upload homework submissions, and view daily class diaries.";

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
                        tabs={[...TABS]}
                        active={activeTab}
                        onChange={(t) => setTab(t as HomeworkTab)}
                    />

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
