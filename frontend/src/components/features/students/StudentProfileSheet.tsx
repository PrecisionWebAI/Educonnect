"use client";

import type { Student } from "@/types";
import { Badge } from "@/components/ui";
import Icon from "@/components/ui/Icon";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetDescription,
} from "@/components/ui/sheet";

function initials(name: string) {
    return name
        .split(" ")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase();
}

export default function StudentProfileSheet({
    student,
    onClose,
}: {
    student: Student | null;
    onClose: () => void;
}) {
    return (
        <Sheet open={student !== null} onOpenChange={(open) => !open && onClose()} modal={false}>
            <SheetContent
                side="right"
                hideOverlay
                className="flex w-full flex-col border-l border-(--border-subtle) bg-linear-to-br from-(--background)/30 to-(--background)/10 p-0 shadow-[-20px_0_60px_-15px_rgba(0,0,0,0.3)] backdrop-blur-3xl sm:max-w-md"
            >
                {student && (
                    <div className="flex-1 overflow-y-auto p-6">
                        <SheetHeader className="mb-8 text-left">
                            <div className="flex items-center gap-4">
                                <div className="bg-primary/20 text-primary flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl text-2xl font-bold shadow-[0_0_15px_rgba(var(--primary),0.3)]">
                                    {initials(student.name)}
                                </div>
                                <div>
                                    <SheetTitle className="text-2xl font-bold">
                                        {student.name}
                                    </SheetTitle>
                                    <SheetDescription className="text-muted-foreground">
                                        Admission No: {student.admissionNo}
                                    </SheetDescription>
                                </div>
                            </div>
                        </SheetHeader>

                        <div className="flex flex-col gap-6">
                            {/* Quick Stats */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="glass-card blob-blue p-4 text-center">
                                    <div className="text-muted-foreground mb-1 text-xs">Status</div>
                                    <Badge
                                        tone={student.status === "Active" ? "green" : "muted"}
                                        className="shadow-sm"
                                    >
                                        {student.status}
                                    </Badge>
                                </div>
                                <div className="glass-card blob-purple p-4 text-center">
                                    <div className="text-muted-foreground mb-1 text-xs">Class</div>
                                    <div className="text-foreground text-lg font-bold">
                                        {student.className}-{student.section}
                                    </div>
                                </div>
                            </div>

                            {/* Details List */}
                            <div className="glass-card space-y-4 border border-(--border-subtle) p-5">
                                <h4 className="text-foreground mb-4 border-b border-(--border-subtle) pb-2 font-semibold">
                                    Personal Details
                                </h4>
                                <div className="flex items-center gap-3">
                                    <div className="text-muted-foreground bg-accent flex h-8 w-8 items-center justify-center rounded-lg">
                                        <Icon name="user" size={16} />
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground text-xs">Gender</div>
                                        <div className="text-foreground text-sm font-medium">
                                            {student.gender}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="text-muted-foreground flex h-8 w-8 items-center justify-center rounded-lg bg-(--accent-surface)">
                                        <Icon name="guardian" size={16} />
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground text-xs">
                                            Guardian
                                        </div>
                                        <div className="text-foreground text-sm font-medium">
                                            {student.guardian}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="text-muted-foreground flex h-8 w-8 items-center justify-center rounded-lg bg-(--accent-surface)">
                                        <Icon name="phone" size={16} />
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground text-xs">
                                            Contact Phone
                                        </div>
                                        <div className="text-foreground text-sm font-medium">
                                            {student.phone}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="text-muted-foreground flex h-8 w-8 items-center justify-center rounded-lg bg-(--accent-surface)">
                                        <Icon name="email" size={16} />
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground text-xs">
                                            Email Address
                                        </div>
                                        <div className="text-foreground text-sm font-medium">
                                            {student.email || "—"}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </SheetContent>
        </Sheet>
    );
}
