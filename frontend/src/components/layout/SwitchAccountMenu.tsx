"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/providers/auth-context";
import { hasPermission } from "@/lib/auth/rbac";
import { Button, Input } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import {
    getImpersonationRoles,
    getScopeSchools,
    searchImpersonationTargets,
    setSchoolScope,
    startImpersonation,
    stopImpersonation,
    type ImpersonationRoleOption,
    type ImpersonationTarget,
    type ScopeSchool,
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

/**
 * A strip under the header while a platform session is looking at one school.
 *
 * The same idea as the impersonation banner, one notch quieter: the identity never
 * changed, only which school's rows this session is bound to. "All schools" hands
 * back the platform-wide token.
 */
export function useBackToAllSchools() {
    const { switchSession } = useAuth();
    const toast = useToast();
    const [busy, setBusy] = useState(false);

    const backToAllSchools = useCallback(async () => {
        setBusy(true);
        try {
            const session = await setSchoolScope(null);
            switchSession(session);
            toast.push("success", "Back to all schools");
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not switch back"));
        } finally {
            setBusy(false);
        }
    }, [switchSession, toast]);

    return { busy, backToAllSchools };
}

/** A strip that sits under the header for as long as a session is impersonated. */
export function ImpersonationBanner() {
    const { user } = useAuth();
    const { busy, returnToSelf } = useReturnToSelf();
    const { busy: clearing, backToAllSchools } = useBackToAllSchools();

    if (user?.impersonatedBy) {
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

    // Platform admin, one school picked: own account, that school's data.
    if (!user?.schoolScope) return null;

    return (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-sky-300/60 bg-sky-100/70 px-4 py-1.5 text-sm text-sky-900 sm:px-6 dark:border-sky-400/25 dark:bg-sky-500/10 dark:text-sky-200">
            <span>
                Viewing <b>{user.schoolName}</b> only — your platform access is unchanged
            </span>
            <button
                type="button"
                onClick={() => void backToAllSchools()}
                disabled={clearing}
                className="underline underline-offset-2 hover:no-underline disabled:opacity-60"
            >
                {clearing ? "Switching…" : "All schools"}
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
    // The "switch school" half: every active school, with its student count.
    const [schools, setSchools] = useState<ScopeSchool[]>([]);
    const [schoolQuery, setSchoolQuery] = useState("");
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

    // The school list, fetched once per page: it only changes when a school is
    // registered or suspended.
    useEffect(() => {
        if (!open || schools.length > 0) return;
        void getScopeSchools()
            .then(setSchools)
            .catch(() => setSchools([]));
    }, [open, schools.length]);

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

    /**
     * "Switch school": stay yourself, see one school - or all of them again.
     *
     * `switchSession` clears the query cache, so the page that is open refetches
     * with the new token and shows the chosen school's numbers rather than the
     * previous ones.
     */
    async function pickSchool(school: ScopeSchool | null) {
        setSwitching(true);
        try {
            const session = await setSchoolScope(school?.id ?? null);
            switchSession(session);
            setOpen(false);
            setSchoolQuery("");
            toast.push("info", school ? `Viewing ${school.name} only` : "Back to all schools");
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not switch school"));
        } finally {
            setSwitching(false);
        }
    }

    const shownSchools = schoolQuery.trim()
        ? schools.filter((school) =>
              `${school.name} ${school.code}`
                  .toLowerCase()
                  .includes(schoolQuery.trim().toLowerCase()),
          )
        : schools;

    // Already viewing somebody else: the only useful action is going back.
    //
    // Checked *before* `allowed`, on purpose. The account being viewed does not
    // hold `users.impersonate`, so testing the permission first hid this button
    // the instant a switch succeeded - leaving the banner as the only way back,
    // and nothing at all if the banner was dismissed or the session reloaded.
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

    // Not the platform admin: this control does not exist for other accounts.
    if (!allowed) return null;

    return (
        <div className="relative" ref={panelRef}>
            <Button variant="outline" size="sm" onClick={() => setOpen((value) => !value)}>
                Switch account
            </Button>

            {open && (
                <div className="bg-popover text-popover-foreground absolute right-0 z-50 mt-2 w-96 rounded-md border p-3 shadow-lg">
                    {/* Switch school first: it keeps the admin's own account, so it
                        is the lighter of the two switches. */}
                    <div className="mb-3 flex items-center justify-between">
                        <span className="text-muted-foreground block text-xs font-medium">
                            School
                        </span>
                        {user?.schoolScope && (
                            <button
                                type="button"
                                disabled={switching}
                                onClick={() => void pickSchool(null)}
                                className="text-xs underline underline-offset-2 hover:no-underline disabled:opacity-60"
                            >
                                All schools
                            </button>
                        )}
                    </div>
                    <Input
                        placeholder="Find a school"
                        value={schoolQuery}
                        onChange={(event) => setSchoolQuery(event.target.value)}
                        className="mb-2"
                    />
                    <div className="mb-3 max-h-40 overflow-y-auto">
                        {schools.length === 0 && (
                            <p className="text-muted-foreground py-1 text-sm">No schools yet.</p>
                        )}
                        {shownSchools.map((school) => (
                            <button
                                key={school.id}
                                type="button"
                                disabled={switching}
                                onClick={() => void pickSchool(school)}
                                className="hover:bg-accent flex w-full items-baseline justify-between gap-2 rounded-md px-2 py-1.5 text-left disabled:opacity-60"
                            >
                                <span className="truncate text-sm">{school.name}</span>
                                <span className="text-muted-foreground shrink-0 text-xs">
                                    {school.students} students
                                </span>
                            </button>
                        ))}
                    </div>

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
