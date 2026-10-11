"use client";
import { Badge, Button, Spinner } from "@/components/ui";
import Icon from "@/components/ui/Icon";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetDescription,
} from "@/components/ui/sheet";
import { useNotifications, type NotificationsTab } from "./useNotifications";
import { useNotificationsContext } from "@/providers/notifications-context";

const TABS: NotificationsTab[] = ["All", "Unread", "Attendance", "Homework", "Alerts"];

const toneMap = {
    Attendance: "amber",
    Homework: "teal",
    Event: "violet",
    Booking: "accent",
    Alert: "red",
    System: "green",
} as const;

export default function NotificationsSheet() {
    const { isOpen, setIsOpen } = useNotificationsContext();
    const n = useNotifications();

    return (
        <Sheet open={isOpen} onOpenChange={setIsOpen} modal={false}>
            <SheetContent
                side="right"
                hideOverlay
                className="flex w-full flex-col border-l border-white/30 bg-linear-to-br from-(--background)/20 to-(--background)/10 p-0 shadow-[-20px_0_60px_-15px_rgba(0,0,0,0.2)] backdrop-blur-[80px]! sm:max-w-md! dark:border-white/10 dark:shadow-[-20px_0_60px_-15px_rgba(0,0,0,0.5)]"
            >
                <div className="flex-1 overflow-y-auto p-6 pb-32">
                    <SheetHeader className="mb-6 text-left">
                        <div className="flex items-center justify-between">
                            <SheetTitle className="flex items-center gap-3 text-2xl font-bold">
                                <div className="bg-primary/20 text-primary flex h-10 w-10 items-center justify-center rounded-xl shadow-[0_0_15px_rgba(var(--primary),0.3)]">
                                    <Icon name="bell" size={24} />
                                </div>
                                <span className="from-primary to-chart-2 bg-linear-to-r bg-clip-text text-transparent">
                                    Notifications
                                </span>
                            </SheetTitle>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={n.markAll}
                                disabled={n.unreadCount === 0}
                                className="hover:bg-accent rounded-full bg-(--card)/50 shadow-sm backdrop-blur-md"
                            >
                                Mark all read
                            </Button>
                        </div>
                        <SheetDescription className="text-muted-foreground text-base">
                            Attendance alerts, homework due reminders and system notices.
                        </SheetDescription>
                    </SheetHeader>

                    {n.loading ? (
                        <div className="flex justify-center py-10">
                            <Spinner />
                        </div>
                    ) : (
                        <div className="flex h-full flex-col space-y-6">
                            <div className="mb-2 flex gap-4">
                                <div className="flex-1 rounded-2xl border border-(--border-subtle) bg-(--accent-surface)/50 p-4 shadow-sm">
                                    <b className="text-foreground text-2xl font-bold">
                                        {n.items.length}
                                    </b>
                                    <span className="text-muted-foreground block text-sm">
                                        Total
                                    </span>
                                </div>
                                <div className="flex-1 rounded-2xl border border-(--border-subtle) bg-(--accent-surface)/50 p-4 shadow-sm">
                                    <b className="text-chart-4 text-2xl font-bold">
                                        {n.unreadCount}
                                    </b>
                                    <span className="text-muted-foreground block text-sm">
                                        Unread
                                    </span>
                                </div>
                            </div>

                            <div className="no-scrollbar flex overflow-x-auto rounded-xl border border-(--border-subtle) bg-(--accent-surface)/40 p-1 shadow-inner backdrop-blur-md">
                                {TABS.map((t) => (
                                    <button
                                        key={t}
                                        onClick={() => n.setTab(t as NotificationsTab)}
                                        className={`min-w-max flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-all ${
                                            n.tab === t
                                                ? "text-foreground border border-(--border-subtle) bg-(--card) shadow-sm"
                                                : "text-muted-foreground hover:text-foreground border border-transparent hover:bg-(--accent-surface)/50"
                                        }`}
                                    >
                                        {t}
                                    </button>
                                ))}
                            </div>

                            <div className="flex-1">
                                {n.filtered.length === 0 ? (
                                    <div className="text-muted-foreground rounded-xl border border-(--border-subtle) bg-(--accent-surface)/30 py-10 text-center">
                                        No notifications match this filter.
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-1 gap-3">
                                        {n.filtered.map((item) => (
                                            <div
                                                key={item.id}
                                                className={`rounded-xl border p-4 transition-all ${item.read ? "border-transparent bg-(--background)/30 opacity-80" : "hover:border-primary border-(--border-subtle) bg-(--card)/80 shadow-(--elev-2) backdrop-blur-md"}`}
                                            >
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="min-w-0">
                                                        <div className="mb-2 flex items-center gap-2">
                                                            <Badge
                                                                tone={
                                                                    toneMap[
                                                                        item.kind as keyof typeof toneMap
                                                                    ]
                                                                }
                                                                className="shadow-sm"
                                                            >
                                                                {item.kind}
                                                            </Badge>
                                                            <b className="text-foreground truncate text-sm">
                                                                {item.title}
                                                            </b>
                                                            {!item.read && (
                                                                <span className="h-2 w-2 shrink-0 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]"></span>
                                                            )}
                                                        </div>
                                                        <p className="text-muted-foreground text-sm">
                                                            {item.body}
                                                        </p>
                                                    </div>
                                                    <span className="text-muted-foreground pt-1 text-xs whitespace-nowrap">
                                                        {item.time}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </SheetContent>
        </Sheet>
    );
}
