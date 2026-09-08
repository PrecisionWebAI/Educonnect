"use client";
import { useState } from "react";
import { getSettingUsers, getSchoolInfo, getSecurityLogs } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type SettingsTab = "Users & Roles" | "School Profile" | "Security" | "Integrations & Prefs";

export function useSettings() {
    const usersQuery = useApiQuery(["settings", "users"], getSettingUsers);
    const infoQuery = useApiQuery(["settings", "school-info"], getSchoolInfo);
    const logsQuery = useApiQuery(["settings", "security-logs"], getSecurityLogs);
    const users = usersQuery.data ?? [];
    const info = infoQuery.data ?? [];
    const logs = logsQuery.data ?? [];
    const loading = usersQuery.isPending || infoQuery.isPending || logsQuery.isPending;
    const [tab, setTab] = useState<SettingsTab>("Users & Roles");

    const activeCount = users.filter((u) => u.status === "Active").length;
    const pendingCount = users.filter((u) => u.status === "Invited").length;

    return { users, info, logs, loading, tab, setTab, activeCount, pendingCount };
}
