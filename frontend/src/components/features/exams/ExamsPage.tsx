"use client";
import { useMemo, useState } from "react";
import { PageHeader, Tabs, Input, Select, Spinner, Button } from "@/components/ui";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, isStudent, isParent, ACADEMIC_STAFF_ROLES } from "@/lib/auth/rbac";
import { useExams, type ExamsTab } from "./useExams";
import AiPaperGenerator from "./AiPaperGenerator";
import QuestionBank from "./QuestionBank";
import PapersView from "./PapersView";
import ConductMarking from "./ConductMarking";
import ScheduleSeating from "./ScheduleSeating";

const ALL_TABS: ExamsTab[] = [
    "AI Paper Generator",
    "Question Bank",
    "My Papers",
    "Conduct & Marking",
    "Schedule & Seating",
];

export default function ExamsPage() {
    const { user } = useAuth();
    const isStudentUser = isStudent(user?.roles);
    const isParentUser = isParent(user?.roles);
    const canManagePapers = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);

    const allowedTabs = useMemo(() => {
        if (isStudentUser || isParentUser) {
            return ["Schedule & Seating" as ExamsTab];
        }
        return ALL_TABS;
    }, [isStudentUser, isParentUser]);

    const [tab, setTab] = useState<ExamsTab>(() =>
        canManagePapers ? "AI Paper Generator" : "Schedule & Seating",
    );
    const activeTab = allowedTabs.includes(tab) ? tab : allowedTabs[0];

    const e = useExams();

    const title = isStudentUser
        ? "My Exam Schedule & Seating"
        : isParentUser
          ? "Child Exam Schedule & Seating"
          : "Exams & AI Papers";

    const subtitle =
        isStudentUser || isParentUser
            ? "View your upcoming exam dates, timings, and seating arrangements."
            : "Generate question papers with AI, manage question bank, conduct & schedule.";

    return (
        <div>
            <PageHeader
                title={title}
                subtitle={subtitle}
                actions={canManagePapers && <Button variant="primary">+ New Paper</Button>}
            />

            {e.loading ? (
                <Spinner />
            ) : (
                <>
                    {canManagePapers && (
                        <div className="stat-tiles">
                            <div className="stat-tile">
                                <b>{e.questions.length}</b>
                                <span>Bank Questions</span>
                            </div>
                            <div className="stat-tile">
                                <b>{e.questionTypes.length}</b>
                                <span>Question Types</span>
                            </div>
                            <div className="stat-tile">
                                <b>{e.papers.length}</b>
                                <span>Drafts / Papers</span>
                            </div>
                            <div className="stat-tile">
                                <b>{e.schedule.length}</b>
                                <span>Exams Scheduled</span>
                            </div>
                        </div>
                    )}

                    <Tabs
                        tabs={allowedTabs}
                        active={activeTab}
                        onChange={(t) => setTab(t as ExamsTab)}
                    />

                    {activeTab === "AI Paper Generator" && canManagePapers && <AiPaperGenerator />}

                    {activeTab === "Question Bank" && canManagePapers && (
                        <>
                            <div className="toolbar">
                                <div className="toolbar-search">
                                    <Input
                                        placeholder="Search question or chapter…"
                                        value={e.query}
                                        onChange={(ev) => e.setQuery(ev.target.value)}
                                    />
                                </div>
                                <Select
                                    value={e.subject}
                                    onChange={(ev) => e.setSubject(ev.target.value)}
                                >
                                    {e.subjects.map((s) => (
                                        <option key={s} value={s}>
                                            {s}
                                        </option>
                                    ))}
                                </Select>
                            </div>
                            <QuestionBank rows={e.filteredQuestions} />
                        </>
                    )}

                    {activeTab === "My Papers" && (
                        <PapersView papers={e.papers} reviews={e.reviews} />
                    )}
                    {activeTab === "Conduct & Marking" && <ConductMarking rows={e.markings} />}
                    {activeTab === "Schedule & Seating" && <ScheduleSeating rows={e.schedule} />}
                </>
            )}
        </div>
    );
}
