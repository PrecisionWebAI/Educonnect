"use client";

import { useMemo, useState } from "react";
import { Badge, Button, PageHeader, Select, Spinner, Table, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, isStudent, isParent, ACADEMIC_STAFF_ROLES } from "@/lib/auth/rbac";
import { getResults, getDisputes } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { ResultRow, DisputeRow } from "@/types";
import { useAcademics } from "./useAcademics";
import MarksEntryTab from "./MarksEntryTab";
import GradebookTab from "./GradebookTab";

// PAGE 05 — Academics & Marks. Container: tabs + shared filters.
export default function AcademicsPage() {
    const toast = useToast();
    const { user } = useAuth();
    const ac = useAcademics();

    const isStudentUser = isStudent(user?.roles);
    const isParentUser = isParent(user?.roles);
    const canEnterMarks = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);

    const allowedTabs = useMemo(() => {
        if (isStudentUser || isParentUser) {
            return ["Results & Analytics", "Marks Dispute"];
        }
        return ["Marks entry", "Gradebook", "Results & Analytics", "Marks Dispute"];
    }, [isStudentUser, isParentUser]);

    const [tab, setTab] = useState(() =>
        canEnterMarks ? "Marks entry" : "Results & Analytics",
    );
    const activeTab = allowedTabs.includes(tab) ? tab : allowedTabs[0];

    const resultsQuery = useApiQuery(["exams", "results"], getResults);
    const disputesQuery = useApiQuery(["exams", "disputes"], getDisputes);
    const results = resultsQuery.data ?? [];
    const disputes = disputesQuery.data ?? [];

    function handleSave() {
        toast.push("success", `Marks saved for ${ac.entries.length} students`);
    }

    const pageTitle = isStudentUser
        ? "My Academics & Results"
        : isParentUser
          ? "Child Academics & Results"
          : "Academics & Marks";

    const pageSubtitle = isStudentUser
        ? "View your exam performance, analytics, and report cards"
        : isParentUser
          ? "Track your child's exam scores, pass rates, and report cards"
          : "Spreadsheet-grade marks entry and gradebook";

    return (
        <div className="page">
            <PageHeader
                title={pageTitle}
                subtitle={pageSubtitle}
                actions={
                    activeTab === "Marks entry" &&
                    canEnterMarks && <Button onClick={handleSave}>Save marks</Button>
                }
            />

            <Tabs tabs={allowedTabs} active={activeTab} onChange={setTab} />

            <div className="toolbar">
                <Select
                    value={ac.exam}
                    onChange={(e) => ac.setExam(e.target.value)}
                    aria-label="Exam"
                >
                    <option value="all">All exams</option>
                    {ac.exams.map((x) => (
                        <option key={x} value={x}>
                            {x}
                        </option>
                    ))}
                </Select>
                <Select
                    value={ac.className}
                    onChange={(e) => ac.setClassName(e.target.value)}
                    aria-label="Class"
                >
                    <option value="all">All classes</option>
                    {ac.classNames.map((c) => (
                        <option key={c} value={c}>
                            {c}
                        </option>
                    ))}
                </Select>
            </div>

            {ac.loading ? (
                <Spinner />
            ) : activeTab === "Marks entry" ? (
                <MarksEntryTab
                    entries={ac.entries}
                    subjects={ac.subjects}
                    onScoreChange={ac.updateScore}
                />
            ) : activeTab === "Gradebook" ? (
                <GradebookTab entries={ac.entries} />
            ) : activeTab === "Results & Analytics" ? (
                <Table
                    columns={[
                        { key: "exam", header: "Exam", render: (r: ResultRow) => <b>{r.exam}</b> },
                        { key: "className", header: "Class" },
                        {
                            key: "passRate",
                            header: "Pass rate",
                            render: (r: ResultRow) => `${r.passRate}%`,
                        },
                        {
                            key: "avgScore",
                            header: "Avg score",
                            render: (r: ResultRow) => `${r.avgScore}%`,
                        },
                        { key: "topper", header: "Topper" },
                    ]}
                    rows={results}
                    rowKey={(r) => r.id}
                    empty="No exam results yet."
                />
            ) : (
                <>
                    <p style={{ color: "var(--muted)", marginBottom: "0.6rem" }}>
                        Students can challenge marks; disputes route to the subject teacher, then
                        HOD.
                    </p>
                    <Table
                        columns={[
                            {
                                key: "student",
                                header: "Student",
                                render: (r: DisputeRow) => <b>{r.student}</b>,
                            },
                            { key: "exam", header: "Exam" },
                            { key: "subject", header: "Subject" },
                            { key: "reason", header: "Reason" },
                            {
                                key: "status",
                                header: "Status",
                                render: (r: DisputeRow) => (
                                    <Badge
                                        tone={
                                            r.status === "Resolved"
                                                ? "green"
                                                : r.status === "Open"
                                                  ? "red"
                                                  : "amber"
                                        }
                                    >
                                        {r.status}
                                    </Badge>
                                ),
                            },
                        ]}
                        rows={disputes}
                        rowKey={(r) => r.id}
                        empty="No mark disputes."
                    />
                </>
            )}
        </div>
    );
}
