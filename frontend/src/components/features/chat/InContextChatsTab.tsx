"use client";

import { useState, useEffect } from "react";
import { Card, Badge, Button, Input, Textarea, Select, Spinner } from "@/components/ui";
import {
    Sparkles,
    Pin,
    ArrowRight,
    UserCheck,
    FileText,
    Ticket,
    Layers,
    Plus,
    CheckCircle2,
} from "lucide-react";
import { getInContextEntities, getClassNotices, createClassNotice } from "@/services";
import type { InContextEntity, ClassNotice } from "@/types";
import { useAuth } from "@/providers/auth-context";
import { isStaff } from "@/lib/auth/rbac";
import { useToast } from "@/components/ui/toast";

interface InContextChatsTabProps {
    onOpenEntityChat: (threadId: number) => void;
}

export function InContextChatsTab({ onOpenEntityChat }: InContextChatsTabProps) {
    const { user } = useAuth();
    const { push } = useToast();
    const canPinNotices = isStaff(user?.roles);

    const [entities, setEntities] = useState<InContextEntity[]>([]);
    const [notices, setNotices] = useState<ClassNotice[]>([]);
    const [loading, setLoading] = useState(true);
    const [entityTypeFilter, setEntityTypeFilter] = useState<string>("all");

    // New Notice Form State
    const [showNewNotice, setShowNewNotice] = useState(false);
    const [noticeTitle, setNoticeTitle] = useState("");
    const [noticeContent, setNoticeContent] = useState("");
    const [noticeClass, setNoticeClass] = useState("Class 10-A");
    const [noticePriority, setNoticePriority] = useState<"Normal" | "Urgent">("Normal");
    const [savingNotice, setSavingNotice] = useState(false);

    useEffect(() => {
        let alive = true;
        Promise.all([getInContextEntities(), getClassNotices()]).then(([ent, not]) => {
            if (alive) {
                setEntities(ent);
                setNotices(not);
                setLoading(false);
            }
        });
        return () => {
            alive = false;
        };
    }, []);

    async function handleCreateNotice(e: React.FormEvent) {
        e.preventDefault();
        if (!noticeTitle.trim() || !noticeContent.trim()) return;

        setSavingNotice(true);
        try {
            const created = await createClassNotice({
                title: noticeTitle,
                content: noticeContent,
                targetClass: noticeClass,
                priority: noticePriority,
                pinnedBy: user?.fullName || "Class Teacher",
            });
            setNotices((prev) => [created, ...prev]);
            push("success", `Notice pinned to ${noticeClass} and broadcast to members.`);
            setNoticeTitle("");
            setNoticeContent("");
            setShowNewNotice(false);
        } catch {
            push("error", "Failed to create notice.");
        } finally {
            setSavingNotice(false);
        }
    }

    const filteredEntities = entities.filter((ent) => {
        if (entityTypeFilter === "all") return true;
        return ent.type === entityTypeFilter;
    });

    if (loading) {
        return (
            <div className="flex justify-center py-12">
                <Spinner />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Top Banner Explainer */}
            <div className="from-primary/10 via-primary/5 to-background flex flex-col justify-between gap-3 rounded-xl border bg-gradient-to-r p-4 md:flex-row md:items-center">
                <div className="flex items-start gap-3">
                    <div className="bg-primary/20 text-primary shrink-0 rounded-lg p-2">
                        <Sparkles className="h-5 w-5" />
                    </div>
                    <div>
                        <h3 className="text-foreground text-sm font-semibold">
                            In-Context Entity Jump & Smart Ticket Bridge
                        </h3>
                        <p className="text-muted-foreground mt-0.5 max-w-2xl text-xs">
                            Every student profile, section roster, support ticket, and exam paper is
                            bound to its live chat room. Informal discussions auto-suggest formal
                            tickets when issue keywords arise.
                        </p>
                    </div>
                </div>
            </div>

            {/* Section 1: Entity Jump Matrix */}
            <div className="space-y-3">
                <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
                    <div>
                        <h4 className="text-foreground text-sm font-semibold">
                            Entity-Bound Quick Chats
                        </h4>
                        <p className="text-muted-foreground text-xs">
                            Jump straight into focused discussion threads with all relevant
                            stakeholders.
                        </p>
                    </div>

                    <div className="flex items-center gap-1 text-xs">
                        {(["all", "student", "class", "ticket", "paper"] as const).map((t) => (
                            <button
                                key={t}
                                type="button"
                                onClick={() => setEntityTypeFilter(t)}
                                className={`rounded-md px-2.5 py-1 font-medium capitalize transition-colors ${
                                    entityTypeFilter === t
                                        ? "bg-primary text-primary-foreground"
                                        : "text-muted-foreground hover:bg-muted"
                                }`}
                            >
                                {t}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
                    {filteredEntities.map((ent) => (
                        <Card
                            key={ent.id}
                            className="flex flex-col justify-between space-y-3 p-3.5"
                        >
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <Badge
                                        tone={
                                            ent.type === "student"
                                                ? "teal"
                                                : ent.type === "class"
                                                  ? "violet"
                                                  : ent.type === "ticket"
                                                    ? "amber"
                                                    : "muted"
                                        }
                                    >
                                        {ent.badge}
                                    </Badge>
                                    {ent.hasActiveIssue && (
                                        <Badge tone="red" className="text-[10px]">
                                            Open Issue
                                        </Badge>
                                    )}
                                </div>

                                <div>
                                    <div className="text-foreground flex items-center gap-1.5 text-sm font-semibold">
                                        {ent.type === "student" && (
                                            <UserCheck className="h-4 w-4 text-teal-600" />
                                        )}
                                        {ent.type === "class" && (
                                            <Layers className="h-4 w-4 text-violet-600" />
                                        )}
                                        {ent.type === "ticket" && (
                                            <Ticket className="h-4 w-4 text-amber-600" />
                                        )}
                                        {ent.type === "paper" && (
                                            <FileText className="h-4 w-4 text-sky-600" />
                                        )}
                                        {ent.title}
                                    </div>
                                    <p className="text-muted-foreground mt-0.5 text-xs">
                                        {ent.subtitle}
                                    </p>
                                </div>

                                <div className="text-muted-foreground text-[11px]">
                                    <span className="text-foreground font-medium">
                                        Stakeholders:{" "}
                                    </span>
                                    {ent.stakeholders.join(", ")}
                                </div>
                            </div>

                            <Button
                                size="sm"
                                variant="outline"
                                className="h-8 w-full text-xs"
                                onClick={() => onOpenEntityChat(ent.threadId)}
                            >
                                Open Entity Chat
                                <ArrowRight className="ml-1 h-3.5 w-3.5" />
                            </Button>
                        </Card>
                    ))}
                </div>
            </div>

            {/* Section 2: Class-Wide Notes & Notices Board (Tab 17.3) */}
            <div className="space-y-3 border-t pt-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h4 className="text-foreground flex items-center gap-1.5 text-sm font-semibold">
                            <Pin className="h-4 w-4 fill-amber-500 text-amber-500" />
                            Class-Wide Notes & Notice Board
                        </h4>
                        <p className="text-muted-foreground mt-0.5 text-xs">
                            High-priority updates pinned across class rooms and pushed as
                            notifications.
                        </p>
                    </div>

                    {canPinNotices && (
                        <Button
                            size="sm"
                            variant="primary"
                            onClick={() => setShowNewNotice(!showNewNotice)}
                            className="h-8 text-xs"
                        >
                            <Plus className="mr-1 h-3.5 w-3.5" />
                            {showNewNotice ? "Cancel" : "Pin New Notice"}
                        </Button>
                    )}
                </div>

                {/* New Notice Form */}
                {showNewNotice && (
                    <Card className="border-amber-300 bg-amber-50/40 p-4 dark:border-amber-800 dark:bg-amber-950/20">
                        <form onSubmit={handleCreateNotice} className="space-y-3">
                            <div className="text-foreground text-xs font-semibold tracking-wide uppercase">
                                Create Pinned Class Notice
                            </div>

                            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                                <div>
                                    <label className="text-foreground text-xs font-medium">
                                        Notice Title
                                    </label>
                                    <Input
                                        placeholder="e.g. No class tomorrow — Assembly at 9:00 AM"
                                        value={noticeTitle}
                                        onChange={(e) => setNoticeTitle(e.target.value)}
                                        className="mt-1 text-xs"
                                        required
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-2">
                                    <div>
                                        <label className="text-foreground text-xs font-medium">
                                            Target Class
                                        </label>
                                        <Select
                                            value={noticeClass}
                                            onChange={(e) => setNoticeClass(e.target.value)}
                                            className="mt-1 text-xs"
                                        >
                                            <option value="Class 10-A">Class 10-A</option>
                                            <option value="Class 10-B">Class 10-B</option>
                                            <option value="All Classes">All Classes</option>
                                        </Select>
                                    </div>
                                    <div>
                                        <label className="text-foreground text-xs font-medium">
                                            Priority
                                        </label>
                                        <Select
                                            value={noticePriority}
                                            onChange={(e) =>
                                                setNoticePriority(
                                                    e.target.value as "Normal" | "Urgent",
                                                )
                                            }
                                            className="mt-1 text-xs"
                                        >
                                            <option value="Normal">Normal</option>
                                            <option value="Urgent">Urgent Alert</option>
                                        </Select>
                                    </div>
                                </div>
                            </div>

                            <div>
                                <label className="text-foreground text-xs font-medium">
                                    Notice Details
                                </label>
                                <Textarea
                                    placeholder="Write full notice instructions for students and parents..."
                                    value={noticeContent}
                                    onChange={(e) => setNoticeContent(e.target.value)}
                                    rows={2}
                                    className="mt-1 text-xs"
                                    required
                                />
                            </div>

                            <div className="flex justify-end gap-2">
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setShowNewNotice(false)}
                                    className="h-8 text-xs"
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    size="sm"
                                    disabled={savingNotice}
                                    className="h-8 text-xs"
                                >
                                    <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                                    Broadcast & Pin Notice
                                </Button>
                            </div>
                        </form>
                    </Card>
                )}

                {/* Notices List */}
                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                    {notices.map((notice) => (
                        <Card
                            key={notice.id}
                            className="space-y-2 border-l-4 border-l-amber-500 p-3.5"
                        >
                            <div className="flex items-center justify-between gap-1">
                                <Badge tone={notice.priority === "Urgent" ? "red" : "amber"}>
                                    {notice.priority}
                                </Badge>
                                <span className="text-muted-foreground text-[11px]">
                                    {notice.createdAt}
                                </span>
                            </div>

                            <h5 className="text-foreground text-xs leading-snug font-semibold">
                                {notice.title}
                            </h5>

                            <p className="text-muted-foreground line-clamp-3 text-xs leading-relaxed">
                                {notice.content}
                            </p>

                            <div className="text-muted-foreground flex items-center justify-between border-t pt-2 text-[10px]">
                                <span>
                                    Target: <b>{notice.targetClass}</b>
                                </span>
                                <span>Pinned by: {notice.pinnedBy}</span>
                            </div>
                        </Card>
                    ))}
                </div>
            </div>
        </div>
    );
}
