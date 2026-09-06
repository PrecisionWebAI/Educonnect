"use client";
import { PageHeader, Tabs, Badge, Button, Spinner } from "@/components/ui";
import { useNotifications, type NotificationsTab } from "./useNotifications";

const TABS: NotificationsTab[] = ["All", "Unread", "Attendance", "Homework", "Alerts"];

const toneMap = {
    Attendance: "amber",
    Homework: "teal",
    Event: "violet",
    Booking: "accent",
    Alert: "red",
    System: "green",
} as const;

export default function NotificationsPage() {
    const n = useNotifications();

    return (
        <div>
            <PageHeader
                title="Notifications"
                subtitle="Attendance alerts, homework due reminders and system notices."
                actions={
                    <Button variant="outline" onClick={n.markAll} disabled={n.unreadCount === 0}>
                        Mark all read
                    </Button>
                }
            />

            {n.loading ? (
                <Spinner />
            ) : (
                <>
                    <div className="stat-tiles">
                        <div className="stat-tile">
                            <b>{n.items.length}</b>
                            <span>Total</span>
                        </div>
                        <div className="stat-tile">
                            <b>{n.unreadCount}</b>
                            <span>Unread</span>
                        </div>
                        <div className="stat-tile">
                            <b>{n.filtered.length}</b>
                            <span>Showing</span>
                        </div>
                    </div>

                    <Tabs
                        tabs={TABS}
                        active={n.tab}
                        onChange={(t) => n.setTab(t as NotificationsTab)}
                    />

                    {n.filtered.length === 0 ? (
                        <div className="empty-state">No notifications match this filter.</div>
                    ) : (
                        <div style={{ display: "grid", gap: "0.6rem" }}>
                            {n.filtered.map((item) => (
                                <div
                                    key={item.id}
                                    className="card"
                                    style={{
                                        opacity: item.read ? 0.62 : 1,
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                        gap: "1rem",
                                    }}
                                >
                                    <div style={{ minWidth: 0 }}>
                                        <div
                                            style={{
                                                display: "flex",
                                                alignItems: "center",
                                                gap: "0.5rem",
                                                marginBottom: "0.25rem",
                                            }}
                                        >
                                            <Badge tone={toneMap[item.kind]}>{item.kind}</Badge>
                                            <b>{item.title}</b>
                                            {!item.read && (
                                                <span
                                                    className="badge badge-accent"
                                                    style={{ fontSize: "0.68rem" }}
                                                >
                                                    new
                                                </span>
                                            )}
                                        </div>
                                        <p
                                            style={{
                                                color: "var(--muted)",
                                                fontSize: "0.85rem",
                                                margin: 0,
                                            }}
                                        >
                                            {item.body}
                                        </p>
                                    </div>
                                    <span
                                        style={{
                                            color: "var(--muted)",
                                            fontSize: "0.8rem",
                                            whiteSpace: "nowrap",
                                        }}
                                    >
                                        {item.time}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
