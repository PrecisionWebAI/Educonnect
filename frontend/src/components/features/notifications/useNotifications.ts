"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getNotifications, markAllNotificationsRead } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { NotificationItem } from "@/types";

export type NotificationsTab = "All" | "Unread" | "Attendance" | "Homework" | "Alerts";

export function useNotifications() {
    const queryClient = useQueryClient();
    const notificationsQuery = useApiQuery(["notifications"], getNotifications);
    const items = notificationsQuery.data ?? [];
    const loading = notificationsQuery.isPending;
    const [tab, setTab] = useState<NotificationsTab>("All");

    const unreadCount = items.filter((i) => !i.read).length;

    const filtered = items.filter((i) => {
        if (tab === "Unread") return !i.read;
        if (tab === "All") return true;
        return i.kind === tab;
    });

    const markAll = () => {
        markAllNotificationsRead().then(() => {
            queryClient.setQueryData<NotificationItem[]>(["notifications"], (prev) =>
                (prev ?? []).map((i) => ({ ...i, read: true })),
            );
        });
    };

    return { items, filtered, loading, tab, setTab, unreadCount, markAll };
}
