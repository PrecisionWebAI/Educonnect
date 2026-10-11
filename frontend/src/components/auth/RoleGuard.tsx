"use client";

import { type ReactNode } from "react";
import Link from "next/link";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole } from "@/lib/auth/rbac";
import type { Role } from "@/types";
import { Button, Card } from "@/components/ui";
import Icon from "@/components/ui/Icon";

interface RoleGuardProps {
    allowedRoles: Role[];
    children: ReactNode;
    fallback?: ReactNode;
}

export default function RoleGuard({ allowedRoles, children, fallback }: RoleGuardProps) {
    const { user } = useAuth();
    const isAllowed = hasAnyRole(user?.roles, allowedRoles);

    if (isAllowed) {
        return <>{children}</>;
    }

    if (fallback) {
        return <>{fallback}</>;
    }

    return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center p-12">
            <Card className="flex w-full max-w-md flex-col items-center gap-4 p-8 text-center">
                <div className="bg-destructive/10 text-destructive flex h-14 w-14 items-center justify-center rounded-full">
                    <Icon name="warning" size={32} />
                </div>
                <div>
                    <h2 className="text-xl font-bold tracking-tight">Access Restricted</h2>
                    <p className="text-muted-foreground mt-1 text-sm">
                        Your account role ({user?.roles?.join(", ") || "Guest"}) does not have
                        permission to view this module.
                    </p>
                </div>
                <Link href="/dashboard">
                    <Button variant="outline" className="mt-2">
                        Return to Dashboard
                    </Button>
                </Link>
            </Card>
        </div>
    );
}
