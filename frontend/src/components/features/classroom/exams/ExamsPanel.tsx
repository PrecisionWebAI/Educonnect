"use client";

import { EmptyState } from "@/components/ui";
import { hasAnyRole, ACADEMIC_STAFF_ROLES } from "@/lib/auth/rbac";
import { useAuth } from "@/providers/auth-context";
import PaperBuilder from "@/components/features/exams/paper-builder/PaperBuilder";
import type { PaperBuilderScope } from "@/types/exam-builder";

// Exams & AI Papers **inside one class-section**.
//
// The builder opens for the room you are standing in: the class is fixed to this
// section, its subjects are offered first, and the Draft/Paper lists show only
// this section's papers. Everything a person makes here is **private to them** —
// the backend scopes every paper and job to `created_by`, and answers 404 to
// anybody else, because an exam must not leak before it is sat.

/** `Class 10` -> `10` — the class as the AI and the source library name it. */
function classNumber(className: string): string {
    return className.replace(/^class\s*/i, "").trim();
}

export default function ExamsPanel({
    classroomId,
    sectionId,
    classLabel,
    className,
    subjects,
}: {
    classroomId: string;
    sectionId: string;
    /** "Class 10-A" — what the banner shows. */
    classLabel: string;
    /** "Class 10" — the class the paper is for. */
    className: string;
    subjects: { id: string; name: string }[];
}) {
    const { user } = useAuth();

    if (!hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES)) {
        return (
            <EmptyState
                icon="edit"
                title="Academic staff only"
                body="The AI Paper Generator is available to academic staff roles."
            />
        );
    }

    const scope: PaperBuilderScope = {
        className: classNumber(className),
        label: classLabel,
        classroomId,
        sectionId,
        subjects,
    };

    return (
        <div>
            <p className="text-muted-foreground mb-3 text-xs">
                Papers for <b>{classLabel}</b> · drafts and generated papers are visible only to
                you, the person who created them.
            </p>
            <PaperBuilder scope={scope} />
        </div>
    );
}
