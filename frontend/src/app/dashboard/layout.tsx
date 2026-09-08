"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-context";
import { NAV_GROUPS } from "@/lib/constants/nav";
import AppLayout from "@/components/layout/AppLayout";

/**
 * Build a path → required permissions map from NAV_GROUPS.
 * This is the single source of truth — no separate ROUTE_ROLES map to maintain.
 */
const ROUTE_PERMISSIONS: Record<string, string[]> = Object.fromEntries(
    NAV_GROUPS.flatMap((g) => g.items)
        .filter((item) => item.permissions && item.permissions.length > 0)
        .map((item) => [item.to, item.permissions!]),
);

function canAccessByPermission(pathname: string, userPermissions?: string[] | null): boolean {
    // Find the most specific matching route prefix
    const requiredPerms = ROUTE_PERMISSIONS[pathname];

    // No restriction defined for this path → allow (e.g. sub-pages like /dashboard/students/123)
    if (!requiredPerms || requiredPerms.length === 0) return true;

    // User has no permissions at all → deny
    if (!userPermissions || userPermissions.length === 0) return false;

    // User needs at least ONE of the required permissions
    return requiredPerms.some((p) => userPermissions.includes(p));
}

// Guard: only logged-in users can see anything under /dashboard.
// Additionally, prevent direct URL access to permission-restricted routes.
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    const { isAuthed, user } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        if (!isAuthed) {
            router.replace("/auth");
            return;
        }
        // Redirect to dashboard home if the user lacks permission for this route
        if (!canAccessByPermission(pathname, user?.permissions)) {
            router.replace("/dashboard");
        }
    }, [isAuthed, pathname, user?.permissions, router]);

    if (!isAuthed) return null;
    if (!canAccessByPermission(pathname, user?.permissions)) return null;

    return <AppLayout>{children}</AppLayout>;
}
