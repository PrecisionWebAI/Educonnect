"use client";
import { Badge, Button, Spinner } from "@/components/ui";
import Icon from "@/components/ui/Icon";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
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
                className="flex w-full flex-col border-l border-white/30 bg-linear-to-br from-(--background)/20 to-(--background)/10 p-0 shadow-[-20px_0_60px_-15px_rgba(0,0,0,0.2)] dark:shadow-[-20px_0_60px_-15px_rgba(0,0,0,0.5)] backdrop-blur-[80px]! sm:max-w-md! dark:border-white/10"
            >
                <div className="flex-1 overflow-y-auto p-6 pb-32">
                    <SheetHeader className="mb-6 text-left">
                        <div className="flex justify-between items-center">
                            <SheetTitle className="flex items-center gap-3 text-2xl font-bold">
                                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary shadow-[0_0_15px_rgba(var(--primary),0.3)]">
                                    <Icon name="bell" size={24} />
                                </div>
                                <span className="from-primary to-chart-2 bg-linear-to-r bg-clip-text text-transparent">
                                    Notifications
                                </span>
                            </SheetTitle>
                            <Button variant="outline" size="sm" onClick={n.markAll} disabled={n.unreadCount === 0} className="shadow-sm rounded-full bg-(--card)/50 backdrop-blur-md hover:bg-accent">
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
                            <div className="flex gap-4 mb-2">
                                <div className="flex-1 bg-(--accent-surface)/50 rounded-2xl p-4 border border-(--border-subtle) shadow-sm">
                                    <b className="text-2xl font-bold text-foreground">{n.items.length}</b>
                                    <span className="block text-sm text-muted-foreground">Total</span>
                                </div>
                                <div className="flex-1 bg-(--accent-surface)/50 rounded-2xl p-4 border border-(--border-subtle) shadow-sm">
                                    <b className="text-2xl font-bold text-chart-4">{n.unreadCount}</b>
                                    <span className="block text-sm text-muted-foreground">Unread</span>
                                </div>
                            </div>

                            <div className="flex p-1 bg-(--accent-surface)/40 backdrop-blur-md rounded-xl border border-(--border-subtle) shadow-inner overflow-x-auto no-scrollbar">
                                {TABS.map((t) => (
                                    <button
                                        key={t}
                                        onClick={() => n.setTab(t as NotificationsTab)}
                                        className={`flex-1 min-w-max px-3 py-2 text-sm font-medium rounded-lg transition-all ${
                                            n.tab === t
                                                ? "bg-(--card) text-foreground shadow-sm border border-(--border-subtle)"
                                                : "text-muted-foreground hover:text-foreground hover:bg-(--accent-surface)/50 border border-transparent"
                                        }`}
                                    >
                                        {t}
                                    </button>
                                ))}
                            </div>

                            <div className="flex-1">
                                {n.filtered.length === 0 ? (
                                    <div className="text-center text-muted-foreground py-10 bg-(--accent-surface)/30 rounded-xl border border-(--border-subtle)">
                                        No notifications match this filter.
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-1 gap-3">
                                        {n.filtered.map((item) => (
                                            <div
                                                key={item.id}
                                                className={`p-4 rounded-xl border transition-all ${item.read ? 'bg-(--background)/30 border-transparent opacity-80' : 'bg-(--card)/80 backdrop-blur-md border-(--border-subtle) shadow-(--elev-2) hover:border-primary'}`}
                                            >
                                                <div className="flex justify-between items-start gap-4">
                                                    <div className="min-w-0">
                                                        <div className="flex items-center gap-2 mb-2">
                                                            <Badge tone={toneMap[item.kind as keyof typeof toneMap]} className="shadow-sm">{item.kind}</Badge>
                                                            <b className="text-sm text-foreground truncate">{item.title}</b>
                                                            {!item.read && (
                                                                <span className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)] shrink-0"></span>
                                                            )}
                                                        </div>
                                                        <p className="text-sm text-muted-foreground">{item.body}</p>
                                                    </div>
                                                    <span className="text-xs text-muted-foreground whitespace-nowrap pt-1">
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
