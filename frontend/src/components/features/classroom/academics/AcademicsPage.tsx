"use client";

import { useMemo, useState } from "react";
import { Button, Card, PageHeader, Select, Spinner, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, isStudent, isParent, ACADEMIC_STAFF_ROLES } from "@/lib/auth/rbac";
import { useClassCatalog } from "@/hooks/use-class-catalog";
import { useAcademics } from "./useAcademics";
import MarksEntryTab from "./MarksEntryTab";
import GradebookTab from "./GradebookTab";

// PAGE 05 — Academics & Marks. Container: tabs + shared filters.
export default function AcademicsPage() {
    const toast = useToast();
    const { user } = useAuth();
    // The class filter is the school's real class list (Nursery ... Class 12),
    // not just the classes that happen to have marks loaded.
    const catalog = useClassCatalog();
    const ac = useAcademics();

    const isStudentUser = isStudent(user?.roles);
    const isParentUser = isParent(user?.roles);
    const canEnterMarks = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);

    // Marks entry and the gradebook are the school's own views of its marks; a
    // student or guardian has no tab here.
    const allowedTabs = useMemo(() => {
        if (isStudentUser || isParentUser) return [] as string[];
        return ["Marks entry", "Gradebook"];
    }, [isStudentUser, isParentUser]);

    const [tab, setTab] = useState(() => (canEnterMarks ? "Marks entry" : "Gradebook"));
    const activeTab = allowedTabs.includes(tab) ? tab : allowedTabs[0];

    function handleSave() {
        toast.push("success", `Marks saved for ${ac.entries.length} students`);
    }

    const pageTitle = isStudentUser
        ? "My Academics"
        : isParentUser
          ? "Child Academics"
          : "Academics & Marks";

    const pageSubtitle = isStudentUser
        ? "Your class, subjects and marks"
        : isParentUser
          ? "Your child's class, subjects and marks"
          : "Spreadsheet-grade marks entry and gradebook";

    if (allowedTabs.length === 0) {
        return (
            <div className="page">
                <PageHeader title={pageTitle} subtitle={pageSubtitle} />
                <Card title="Marks are the school's record">
                    <p className="text-muted-foreground text-sm">
                        Marks entry and the gradebook belong to the school&apos;s academic staff.
                    </p>
                </Card>
            </div>
        );
    }

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
                    {catalog.classNames.map((c) => (
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
            ) : (
                <GradebookTab entries={ac.entries} />
            )}
        </div>
    );
}
