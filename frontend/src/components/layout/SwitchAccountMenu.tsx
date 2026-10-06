"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/providers/auth-context";
import { hasPermission } from "@/lib/auth/rbac";
import { Button, Input } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import {
    getImpersonationRoles,
    searchImpersonationTargets,
    startImpersonation,
    stopImpersonation,
    type ImpersonationRoleOption,
    type ImpersonationTarget,
} from "@/services/impersonation.service";

// ============================================================
// Super-admin "switch account".
//
// Rendered only for a session that holds `users.impersonate` - granted to the
// platform-admin role alone. The backend enforces that independently (every
// /auth/impersonate route answers 403 for anybody else), so this gate is
// convenience, not the security boundary.
//
// Two dropdowns, as asked: first a role, then a person holding it. Each person is
// shown as **name on top, role underneath**, and the same list answers an e-mail
// search without touching the role dropdown.
// ============================================================

/**
 * Go back to the administrator's own account.
 *
 * Shared by the header control and the banner so "Return" behaves identically in
 * both places. It needs no stored copy of the admin's token: the switched token
 * carries the actor in its `act` claim, so the API can hand a fresh one back.
 */
export function useReturnToSelf() {
    const { switchSession } = useAuth();
    const toast = useToast();
    const [busy, setBusy] = useState(false);

    const returnToSelf = useCallback(async () => {
        setBusy(true);
        try {
            const session = await stopImpersonation();
            switchSession(session);
            toast.push("success", `Back as ${session.user.fullName}`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not return to your account"));
        } finally {
            setBusy(false);
        }
    }, [switchSession, toast]);

    return { busy, returnToSelf };
}

/** A strip that sits under the header for as long as a session is impersonated. */
export function ImpersonationBanner() {
    const { user } = useAuth();
    const { busy, returnToSelf } = useReturnToSelf();

    if (!user?.impersonatedBy) return null;

    return (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-amber-300/60 bg-amber-100/70 px-4 py-1.5 text-sm text-amber-900 sm:px-6 dark:border-amber-400/25 dark:bg-amber-500/10 dark:text-amber-200">
            <span>
                Viewing as <b>{user.fullName}</b> — signed in as{" "}
                <b>{user.impersonatedBy.fullName}</b>
            </span>
            <button
                type="button"
                onClick={() => void returnToSelf()}
                disabled={busy}
                className="underline underline-offset-2 hover:no-underline disabled:opacity-60"
            >
                {busy ? "Returning…" : "Return to my account"}
            </button>
        </div>
    );
}


export default function SwitchAccountMenu() {
    const { user, switchSession } = useAuth();
    const toast = useToast();
    const { busy: returning, returnToSelf } = useReturnToSelf();

    const [open, setOpen] = useState(false);
    const [roles, setRoles] = useState<ImpersonationRoleOption[]>([]);
    const [role, setRole] = useState("");
    const [search, setSearch] = useState("");
    const [targets, setTargets] = useState<ImpersonationTarget[]>([]);
    const [loadingTargets, setLoadingTargets] = useState(false);
    const [switching, setSwitching] = useState(false);
    const panelRef = useRef<HTMLDivElement>(null);

    // The backend is the boundary here: every /auth/impersonate route answers 403
    // for anyone but the platform admin. The check below therefore also accepts
    // the super-admin role itself, so a session stored before this permission
    // existed still shows the control instead of looking broken.
    const allowed =
        hasPermission(user?.permissions, "users.impersonate") ||
        (user?.roles ?? []).includes("SYSTEM_ADMIN");

    // Close on an outside click: a picker left open over the page is just noise.
    useEffect(() => {
        if (!open) return;
        function onPointerDown(event: MouseEvent) {
            if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
                setOpen(false);
            }
        }
        document.addEventListener("mousedown", onPointerDown);
        return () => document.removeEventListener("mousedown", onPointerDown);
    }, [open]);

    // Dropdown 1: the roles that actually have active people, with their counts.
    useEffect(() => {
        if (!open || roles.length > 0) return;
        void getImpersonationRoles()
            .then(setRoles)
            .catch(() => setRoles([]));
    }, [open, roles.length]);

    // Dropdown 2: follows both the role and the search box (debounced).
    useEffect(() => {
        if (!open) return;
        const handle = setTimeout(() => {
            setLoadingTargets(true);
            void searchImpersonationTargets({
                role: role || undefined,
                search: search || undefined,
            })
                .then(setTargets)
                .catch(() => setTargets([]))
                .finally(() => setLoadingTargets(false));
        }, 250);
        return () => clearTimeout(handle);
    }, [open, role, search]);

    async function switchTo(target: ImpersonationTarget) {
        setSwitching(true);
        try {
            const session = await startImpersonation(target.id);
            switchSession(session);
            setOpen(false);
            setSearch("");
            toast.push("info", `Viewing the app as ${session.user.fullName}`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not switch account"));
        } finally {
            setSwitching(false);
        }
    }

    // Not the platform admin: this control does not exist for other accounts.
    if (!allowed) return null;

    // Already viewing somebody else: the only useful action is going back.
    if (user?.impersonatedBy) {
        return (
            <Button
                variant="outline"
                size="sm"
                loading={returning}
                onClick={() => void returnToSelf()}
            >
                Return to my account
            </Button>
        );
    }

    return (
        <div className="relative" ref={panelRef}>
            <Button variant="outline" size="sm" onClick={() => setOpen((value) => !value)}>
                Switch account
            </Button>

            {open && (
                <div className="bg-popover text-popover-foreground absolute right-0 z-50 mt-2 w-80 rounded-md border p-3 shadow-lg">
                    <label className="text-muted-foreground mb-1 block text-xs font-medium">
                        Role
                    </label>
                    <select
                        className="border-input bg-background mb-3 w-full rounded-md border px-2 py-1.5 text-sm"
                        value={role}
                        onChange={(event) => setRole(event.target.value)}
                    >
                        <option value="">All roles</option>
                        {roles.map((option) => (
                            <option key={option.codename} value={option.codename}>
                                {option.label} ({option.users})
                            </option>
                        ))}
                    </select>

                    <label className="text-muted-foreground mb-1 block text-xs font-medium">
                        Search by e-mail or name
                    </label>
                    <Input
                        placeholder="priya@educonnect.com"
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        className="mb-3"
                    />

                    <div className="max-h-72 overflow-y-auto">
                        {loadingTargets && (
                            <p className="text-muted-foreground py-2 text-sm">Searching…</p>
                        )}
                        {!loadingTargets && targets.length === 0 && (
                            <p className="text-muted-foreground py-2 text-sm">
                                No matching account.
                            </p>
                        )}
                        {targets.map((target) => (
                            <button
                                key={target.id}
                                type="button"
                                disabled={switching}
                                onClick={() => void switchTo(target)}
                                className="hover:bg-accent flex w-full flex-col items-start rounded-md px-2 py-1.5 text-left disabled:opacity-60"
                            >
                                {/* Name on top, role underneath - the same shape the
                                    header uses for the signed-in person. */}
                                <span className="text-sm font-medium">{target.full_name}</span>
                                <span className="text-muted-foreground text-xs">
                                    {target.role_label} · {target.email}
                                </span>
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

