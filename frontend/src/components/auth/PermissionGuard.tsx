"use client";

import React from "react";
import { usePermission } from "../../hooks/use-authorization";

interface PermissionGuardProps {
    permission: string;
    children: React.ReactNode;
    fallback?: React.ReactNode;
}

/**
 * Conditionally renders children if the user has the required permission.
 */
export function PermissionGuard({ permission, children, fallback = null }: PermissionGuardProps) {
    const allowed = usePermission(permission);

    if (!allowed) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
}
