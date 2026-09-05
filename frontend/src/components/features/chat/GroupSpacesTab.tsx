"use client";

import { useState, useEffect } from "react";
import { Card, Badge, Button, Spinner, type BadgeTone } from "@/components/ui";
import { Users, Shield, MessageSquare, Lock, Unlock, Megaphone } from "lucide-react";
import { getGroupSpaces } from "@/services";
import type { GroupSpace } from "@/types";
import { useAuth } from "@/providers/auth-context";
import { isStaff } from "@/lib/auth/rbac";
import { useToast } from "@/components/ui/toast";

interface GroupSpacesTabProps {
    onOpenSpaceChat: (threadId: number) => void;
}

export function GroupSpacesTab({ onOpenSpaceChat }: GroupSpacesTabProps) {
    const { user } = useAuth();
    const { push } = useToast();
    const canManageSpaces = isStaff(user?.roles);

    const [spaces, setSpaces] = useState<GroupSpace[]>([]);
    const [loading, setLoading] = useState(true);
    const [categoryFilter, setCategoryFilter] = useState<string>("all");

    useEffect(() => {
        let alive = true;
        getGroupSpaces().then((data) => {
            if (alive) {
                setSpaces(data);
                setLoading(false);
            }
        });
        return () => {
            alive = false;
        };
    }, []);

    function togglePostingPolicy(spaceId: number) {
        setSpaces((prev) =>
            prev.map((s) => {
                if (s.id === spaceId) {
                    const next = s.whoCanPost === "teachers_only" ? "all" : "teachers_only";
                    push(
                        "success",
                        `Posting policy for ${s.name} changed to ${next === "teachers_only" ? "Teachers Only" : "All Members"}.`,
                    );
                    return { ...s, whoCanPost: next, isAnnouncementChannel: next === "teachers_only" };
                }
                return s;
            }),
        );
    }

    const filtered = spaces.filter((s) => {
        if (categoryFilter === "all") return true;
        return s.category === categoryFilter;
    });

    const categoryTone: Record<GroupSpace["category"], BadgeTone> = {
        class: "teal",
        department: "violet",
        subject_team: "amber",
        club: "green",
    };

    if (loading) {
        return (
            <div className="py-12 flex justify-center">
                <Spinner />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Header and filters */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-muted/20 p-4 rounded-xl border">
                <div>
                    <h3 className="text-sm font-semibold text-foreground">
                        Class Spaces & Department Channels
                    </h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        Governed communication hubs with granular who-can-post posting permissions and announcement broadcasts.
                    </p>
                </div>

                <div className="flex items-center gap-1">
                    {(["all", "class", "department", "subject_team", "club"] as const).map((cat) => (
                        <button
                            key={cat}
                            type="button"
                            onClick={() => setCategoryFilter(cat)}
                            className={`px-2.5 py-1 rounded-lg text-xs font-medium capitalize transition-colors ${
                                categoryFilter === cat
                                    ? "bg-primary text-primary-foreground"
                                    : "text-muted-foreground hover:bg-muted"
                            }`}
                        >
                            {cat.replace("_", " ")}
                        </button>
                    ))}
                </div>
            </div>

            {/* Spaces Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filtered.map((space) => (
                    <Card key={space.id} className="flex flex-col justify-between p-4 space-y-3">
                        <div className="space-y-2">
                            <div className="flex items-start justify-between gap-2">
                                <Badge tone={categoryTone[space.category]}>
                                    {space.category.replace("_", " ")}
                                </Badge>
                                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                    <Users className="h-3.5 w-3.5" />
                                    {space.membersCount} members
                                </span>
                            </div>

                            <div>
                                <h4 className="font-semibold text-sm text-foreground">{space.name}</h4>
                                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                                    {space.description}
                                </p>
                            </div>

                            {/* Active notice snippet */}
                            {space.activeNotice && (
                                <div className="p-2 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-1.5">
                                    <Megaphone className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                                    <span className="line-clamp-2">
                                        <b>Notice:</b> {space.activeNotice}
                                    </span>
                                </div>
                            )}

                            {/* Posting policy status */}
                            <div className="pt-1 flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">Posting Rule:</span>
                                {space.whoCanPost === "teachers_only" ? (
                                    <span className="flex items-center gap-1 font-medium text-amber-600 dark:text-amber-400">
                                        <Lock className="h-3 w-3" />
                                        Teachers & Admins Only
                                    </span>
                                ) : (
                                    <span className="flex items-center gap-1 font-medium text-emerald-600 dark:text-emerald-400">
                                        <Unlock className="h-3 w-3" />
                                        Open Discussion
                                    </span>
                                )}
                            </div>

                            <div className="text-[11px] text-muted-foreground">
                                Moderator: <span className="font-medium text-foreground">{space.moderator}</span>
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="pt-2 border-t flex items-center justify-between gap-2">
                            {canManageSpaces && (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    className="text-xs h-8 px-2"
                                    onClick={() => togglePostingPolicy(space.id)}
                                >
                                    <Shield className="h-3.5 w-3.5 mr-1" />
                                    Toggle Policy
                                </Button>
                            )}

                            <Button
                                size="sm"
                                variant="primary"
                                className="text-xs h-8 px-3 ml-auto"
                                onClick={() => onOpenSpaceChat(space.threadId)}
                            >
                                <MessageSquare className="h-3.5 w-3.5 mr-1" />
                                Open Space Chat
                            </Button>
                        </div>
                    </Card>
                ))}
            </div>
        </div>
    );
}
