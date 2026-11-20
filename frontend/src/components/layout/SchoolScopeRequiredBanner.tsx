"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { Select } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { hasPermission } from "@/lib/auth/rbac";
import { useAuth } from "@/providers/auth-context";
import {
    getScopeSchools,
    setSchoolScope,
    type ScopeSchool,
} from "@/services/impersonation.service";

/**
 * A platform admin can sign in without a school. The API is tenant-scoped, so
 * that session has no students, no teachers and no current academic year until a
 * school is chosen. This banner makes that missing scope explicit and switches
 * the session in one step instead of leaving the data pages looking empty.
 */
export default function SchoolScopeRequiredBanner() {
    const { user, switchSession } = useAuth();
    const toast = useToast();
    const queryClient = useQueryClient();
    const [schools, setSchools] = useState<ScopeSchool[]>([]);
    const [busy, setBusy] = useState(false);

    const canChoose =
        !user?.schoolId &&
        (hasPermission(user?.permissions, "users.impersonate") ||
            (user?.roles ?? []).includes("SYSTEM_ADMIN"));

    useEffect(() => {
        if (!canChoose) return;
        void getScopeSchools()
            .then(setSchools)
            .catch(() => setSchools([]));
    }, [canChoose]);

    if (!canChoose) return null;

    async function choose(schoolId: string) {
        if (!schoolId) return;
        setBusy(true);
        try {
            const session = await setSchoolScope(schoolId);
            switchSession(session);
            await queryClient.invalidateQueries();
            toast.push("success", `Now viewing ${session.user.schoolName ?? "the school"}`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not select the school"));
        } finally {
            setBusy(false);
        }
    }

    return (
        <div
            role="status"
            className="border-primary/30 bg-primary/5 text-foreground mb-4 rounded-lg border p-4 text-sm"
        >
            <p className="font-semibold">Select a school to load students and teachers.</p>
            <p className="text-muted-foreground mt-1">
                You are signed in as a platform admin. Choose the school whose data
                you want to work on.
            </p>
            <div className="mt-3 max-w-sm">
                <Select
                    aria-label="Select a school"
                    value=""
                    disabled={busy || schools.length === 0}
                    onChange={(event) => void choose(event.target.value)}
                >
                    <option value="">
                        {schools.length === 0 ? "Loading schools…" : "Select a school…"}
                    </option>
                    {schools.map((school) => (
                        <option key={school.id} value={school.id}>
                            {school.name} ({school.students} students)
                        </option>
                    ))}
                </Select>
            </div>
        </div>
    );
}
