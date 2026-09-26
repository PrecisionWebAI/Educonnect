"use client";

// ============================================================
// Exams page — sirf AI Paper Generator (PaperBuilder).
//
// Purane tabs (Question Bank / My Papers / Conduct & Marking /
// Schedule & Seating) aur unka dummy data frontend + backend se
// poora hata diya gaya hai. Ab yahan PaperBuilder wizard hi
// render hota hai (blueprint §1.0).
// ============================================================

import { EmptyState, PageHeader } from "@/components/ui";
import { hasAnyRole, ACADEMIC_STAFF_ROLES } from "@/lib/auth/rbac";
import { useAuth } from "@/providers/auth-context";
import AiPaperGenerator from "./AiPaperGenerator";

export default function ExamsPage() {
    const { user } = useAuth();
    const canManagePapers = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);

    if (!canManagePapers) {
        return (
            <div>
                <PageHeader title="Exams & AI Papers" />
                <EmptyState
                    icon="edit"
                    title="Academic staff only"
                    body="The AI Paper Generator is available to academic staff roles."
                />
            </div>
        );
    }

    return (
        <div>
            <PageHeader
                title="Exams & AI Papers"
                            />
            <AiPaperGenerator />
        </div>
    );
}
