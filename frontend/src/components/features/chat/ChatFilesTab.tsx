"use client";

import { useState, useEffect } from "react";
import { Table, Badge, Button, Spinner, Input } from "@/components/ui";
import {
    FileText,
    FileAudio,
    ExternalLink,
    ShieldCheck,
    ShieldAlert,
    Search,
    Download,
    Lock,
} from "lucide-react";
import { getChatFiles } from "@/services";
import type { ChatFile } from "@/types";

interface ChatFilesTabProps {
    onOpenSafeLink: (url: string, name: string) => void;
}

export function ChatFilesTab({ onOpenSafeLink }: ChatFilesTabProps) {
    const [files, setFiles] = useState<ChatFile[]>([]);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState("");

    useEffect(() => {
        let alive = true;
        getChatFiles().then((data) => {
            if (alive) {
                setFiles(data);
                setLoading(false);
            }
        });
        return () => {
            alive = false;
        };
    }, []);

    const filtered = files.filter((f) => {
        if (!query.trim()) return true;
        return (
            f.name.toLowerCase().includes(query.toLowerCase()) ||
            f.sharedBy.toLowerCase().includes(query.toLowerCase())
        );
    });

    const columns = [
        {
            key: "name",
            header: "Resource / Attachment",
            render: (f: ChatFile) => (
                <div className="flex items-center gap-2.5">
                    {f.type === "audio" ? (
                        <FileAudio className="h-4 w-4 shrink-0 text-amber-500" />
                    ) : f.type === "link" ? (
                        <ExternalLink className="h-4 w-4 shrink-0 text-blue-500" />
                    ) : (
                        <FileText className="h-4 w-4 shrink-0 text-rose-500" />
                    )}
                    <span className="text-foreground max-w-[280px] truncate text-xs font-semibold">
                        {f.name}
                    </span>
                </div>
            ),
        },
        {
            key: "sharedBy",
            header: "Shared By",
            render: (f: ChatFile) => (
                <span className="text-muted-foreground text-xs">{f.sharedBy}</span>
            ),
        },
        {
            key: "size",
            header: "Size & Limit",
            render: (f: ChatFile) => (
                <span className="text-muted-foreground text-xs">
                    {f.size} <span className="text-[10px] text-emerald-600">(&lt;25MB)</span>
                </span>
            ),
        },
        {
            key: "safeStatus",
            header: "Security Audit",
            render: (f: ChatFile) => (
                <div className="flex items-center gap-1.5">
                    {f.safeStatus === "external" ? (
                        <Badge tone="amber" className="flex items-center gap-1 text-[10px]">
                            <ShieldAlert className="h-3 w-3" />
                            External Link
                        </Badge>
                    ) : (
                        <Badge tone="green" className="flex items-center gap-1 text-[10px]">
                            <ShieldCheck className="h-3 w-3" />
                            Antivirus Verified
                        </Badge>
                    )}
                </div>
            ),
        },
        {
            key: "when",
            header: "Shared",
            render: (f: ChatFile) => (
                <span className="text-muted-foreground text-xs">{f.when}</span>
            ),
        },
        {
            key: "actions",
            header: "Actions",
            render: (f: ChatFile) => (
                <div className="flex items-center justify-end gap-1.5">
                    <Button
                        size="sm"
                        variant="outline"
                        className="h-7 px-2 text-[11px]"
                        onClick={() =>
                            onOpenSafeLink(f.url || "https://educonnect.internal", f.name)
                        }
                    >
                        <Lock className="mr-1 h-3 w-3" />
                        Verify & Open
                    </Button>
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 w-7 p-0"
                        title="Download Attachment"
                        onClick={() =>
                            onOpenSafeLink(f.url || "https://educonnect.internal", f.name)
                        }
                    >
                        <Download className="h-3.5 w-3.5" />
                    </Button>
                </div>
            ),
        },
    ];

    if (loading) {
        return (
            <div className="flex justify-center py-12">
                <Spinner />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Search and info bar */}
            <div className="bg-muted/20 flex flex-col justify-between gap-3 rounded-xl border p-4 sm:flex-row sm:items-center">
                <div>
                    <h3 className="text-foreground text-sm font-semibold">
                        Shared Files & Safe-Link Repository
                    </h3>
                    <p className="text-muted-foreground mt-0.5 text-xs">
                        All files shared across classroom chats and departments are screened with
                        our 25MB limit and AI Safe-Link Shield.
                    </p>
                </div>

                <div className="relative w-full sm:w-64">
                    <Search className="text-muted-foreground absolute top-2.5 left-2.5 h-3.5 w-3.5" />
                    <Input
                        placeholder="Search shared files..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="h-8 pl-8 text-xs"
                    />
                </div>
            </div>

            {/* Table */}
            <Table
                columns={columns}
                rows={filtered}
                rowKey={(f) => f.id}
                empty="No files found matching your search."
            />
        </div>
    );
}
