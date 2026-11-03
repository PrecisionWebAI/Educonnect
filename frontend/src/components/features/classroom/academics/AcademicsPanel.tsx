"use client";

import { useState } from "react";
import { Button, Select, Spinner, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { ACADEMIC_STAFF_ROLES, hasAnyRole } from "@/lib/auth/rbac";
import { errorMessage } from "@/lib/api/client";
import { useAcademics } from "./useAcademics";
import MarksEntryTab from "./MarksEntryTab";
import GradebookTab from "./GradebookTab";

// Marks **inside one class-section**.
//
// The same Marks entry and Gradebook the school-wide screen used, scoped to the
// students of the section the page is showing, and Save now writes for real
// (`PUT /classroom/sections/{id}/marks`, upsert per exam/student/subject).

const TABS = ["Marks entry", "Gradebook"] as const;

export default function AcademicsPanel({ sectionId }: { sectionId: string }) {
    const toast = useToast();
    const { user } = useAuth();
    const canEnterMarks = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);
    const ac = useAcademics({ sectionId });
    const [tab, setTab] = useState<(typeof TABS)[number]>("Marks entry");
    const [error, setError] = useState<string | null>(null);

    async function handleSave() {
        setError(null);
        try {
            const written = await ac.save();
            if (written === 0) {
                toast.push("info", "Pick one exam first — marks are saved per exam.");
                return;
            }
            toast.push("success", `Marks saved for ${written} score(s)`);
        } catch (cause) {
            const message = errorMessage(cause, "Could not save the marks");
            setError(message);
            toast.push("error", message);
        }
    }

    if (ac.loading) return <Spinner />;

    return (
        <div className="space-y-4">
            <div className="toolbar">
                <Select
                    value={ac.exam}
                    onChange={(e) => ac.setExam(e.target.value)}
                    aria-label="Exam"
                >
                    <option value="all">All exams</option>
                    {ac.exams.map((name) => (
                        <option key={name} value={name}>
                            {name}
                        </option>
                    ))}
                </Select>
                {canEnterMarks && ac.canSave && (
                    <Button
                        onClick={handleSave}
                        disabled={ac.saving || ac.exam === "all" || ac.entries.length === 0}
                    >
                        {ac.saving ? "Saving…" : "Save marks"}
                    </Button>
                )}
            </div>

            {error && <p className="text-sm text-red-500">{error}</p>}

            {ac.entries.length === 0 ? (
                <div className="glass-tile rounded-2xl p-8 text-center">
                    <p className="text-muted-foreground text-sm">
                        No marks recorded for this class-section yet.
                    </p>
                </div>
            ) : (
                <>
                    <Tabs
                        tabs={[...TABS]}
                        active={tab}
                        onChange={(next) => setTab(next as (typeof TABS)[number])}
                    />
                    <div className="mt-4">
                        {tab === "Marks entry" ? (
                            <MarksEntryTab
                                entries={ac.entries}
                                subjects={ac.subjects}
                                onScoreChange={ac.updateScore}
                            />
                        ) : (
                            <GradebookTab entries={ac.entries} />
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
