import type { NotificationItem } from "@/types";

const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms));

export async function getNotifications(): Promise<NotificationItem[]> {
    await delay();
    const items: NotificationItem[] = [
        {
            id: 1,
            kind: "Attendance",
            title: "Diya absent",
            body: "Periods 2-3 physical",
            time: "10m",
            read: false,
            to: "Teacher",
        },
        {
            id: 2,
            kind: "Homework",
            title: "Hw reminder",
            body: "Trig sheet due tomorrow",
            time: "35m",
            read: true,
            to: "Teacher",
        },
    ];
    return items;
}

export async function markAllNotificationsRead(): Promise<void> {
    await delay(100);
}
