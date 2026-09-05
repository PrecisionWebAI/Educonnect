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
                        <FileAudio className="h-4 w-4 text-amber-500 shrink-0" />
                    ) : f.type === "link" ? (
                        <ExternalLink className="h-4 w-4 text-blue-500 shrink-0" />
                    ) : (
                        <FileText className="h-4 w-4 text-rose-500 shrink-0" />
                    )}
                    <span className="font-semibold text-xs text-foreground truncate max-w-[280px]">
                        {f.name}
                    </span>
                </div>
            ),
        },
        {
            key: "sharedBy",
            header: "Shared By",
            render: (f: ChatFile) => <span className="text-xs text-muted-foreground">{f.sharedBy}</span>,
        },
        {
            key: "size",
            header: "Size & Limit",
            render: (f: ChatFile) => (
                <span className="text-xs text-muted-foreground">
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
                        <Badge tone="amber" className="text-[10px] flex items-center gap-1">
                            <ShieldAlert className="h-3 w-3" />
                            External Link
                        </Badge>
                    ) : (
                        <Badge tone="green" className="text-[10px] flex items-center gap-1">
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
            render: (f: ChatFile) => <span className="text-xs text-muted-foreground">{f.when}</span>,
        },
        {
            key: "actions",
            header: "Actions",
            render: (f: ChatFile) => (
                <div className="flex items-center gap-1.5 justify-end">
                    <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-[11px] px-2"
                        onClick={() => onOpenSafeLink(f.url || "https://educonnect.internal", f.name)}
                    >
                        <Lock className="h-3 w-3 mr-1" />
                        Verify & Open
                    </Button>
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 w-7 p-0"
                        title="Download Attachment"
                        onClick={() => onOpenSafeLink(f.url || "https://educonnect.internal", f.name)}
                    >
                        <Download className="h-3.5 w-3.5" />
                    </Button>
                </div>
            ),
        },
    ];

    if (loading) {
        return (
            <div className="py-12 flex justify-center">
                <Spinner />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Search and info bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-muted/20 p-4 rounded-xl border">
                <div>
                    <h3 className="text-sm font-semibold text-foreground">
                        Shared Files & Safe-Link Repository
                    </h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        All files shared across classroom chats and departments are screened with our 25MB limit and AI Safe-Link Shield.
                    </p>
                </div>

                <div className="relative w-full sm:w-64">
                    <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                    <Input
                        placeholder="Search shared files..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="pl-8 h-8 text-xs"
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
