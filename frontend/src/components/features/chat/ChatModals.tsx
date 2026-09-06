"use client";

import { useState, useEffect } from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    Button,
    Input,
    Select,
    Textarea,
    Badge,
    Spinner,
    type BadgeTone,
} from "@/components/ui";
import { ShieldCheck, ShieldAlert, Lock, AlertTriangle, MessageSquarePlus, UserCheck } from "lucide-react";
import type { ChatContact } from "@/types";
import { getChatContacts } from "@/services";

// ============================================================
// 1. Safe-Link Shield Modal
// ============================================================

interface SafeLinkModalProps {
    open: boolean;
    url: string;
    name: string;
    onClose: () => void;
}

export function SafeLinkModal({ open, url, name, onClose }: SafeLinkModalProps) {
    if (!open) return null;

    const isInternal = url.includes("educonnect.internal") || url.startsWith("/");

    return (
        <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
            <DialogContent className="sm:max-w-120">
                <DialogHeader>
                    <div className="flex items-center gap-2 text-primary">
                        <ShieldCheck className="h-5 w-5 text-emerald-500" />
                        <DialogTitle>EduConnect Safe-Link Shield 🤖</DialogTitle>
                    </div>
                </DialogHeader>

                <div className="space-y-3 py-2 text-sm">
                    <div className="rounded-lg border bg-muted/40 p-3">
                        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                            Target Resource
                        </div>
                        <div className="mt-1 font-medium text-foreground break-all">{name || url}</div>
                        <div className="mt-1 text-xs text-muted-foreground break-all">{url}</div>
                    </div>

                    <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">Scan Status:</span>
                        {isInternal ? (
                            <Badge tone="green">Verified School Internal Network</Badge>
                        ) : (
                            <Badge tone="amber">External Destination</Badge>
                        )}
                    </div>

                    <p className="text-xs text-muted-foreground leading-relaxed">
                        {isInternal
                            ? "This resource is hosted on EduConnect's secure internal cloud storage and has passed automated antivirus screening."
                            : "You are about to navigate to an external third-party domain. Never enter your school credentials, login password, or financial PINs outside EduConnect."}
                    </p>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                    <Button variant="outline" size="sm" onClick={onClose}>
                        Go Back
                    </Button>
                    <Button
                        size="sm"
                        onClick={() => {
                            window.open(url, "_blank", "noopener,noreferrer");
                            onClose();
                        }}
                    >
                        Proceed to Link
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}

// ============================================================
// 2. PIN Verification Modal (Sensitive Info)
// ============================================================

interface PinModalProps {
    open: boolean;
    messageId: number | null;
    onClose: () => void;
    onUnlock: (messageId: number, pin: string) => void;
}

export function PinModal({ open, messageId, onClose, onUnlock }: PinModalProps) {
    const [pin, setPin] = useState("");

    if (!open || !messageId) return null;

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        onUnlock(messageId!, pin);
        setPin("");
    }

    return (
        <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
            <DialogContent className="sm:max-w-[400px]">
                <DialogHeader>
                    <div className="flex items-center gap-2 text-primary">
                        <Lock className="h-5 w-5 text-amber-500" />
                        <DialogTitle>Sensitive Information Lock</DialogTitle>
                    </div>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-3 py-2 text-sm">
                    <p className="text-xs text-muted-foreground">
                        This message contains confidential financial or student record details. Enter your 4-digit security PIN to decrypt.
                    </p>

                    <div>
                        <label className="text-xs font-medium text-foreground">Security PIN Code</label>
                        <Input
                            type="password"
                            maxLength={4}
                            placeholder="Enter 4-digit PIN (default: 1234)"
                            value={pin}
                            onChange={(e) => setPin(e.target.value)}
                            autoFocus
                            className="mt-1 text-center text-lg tracking-widest"
                        />
                        <span className="text-[11px] text-muted-foreground mt-1 block">
                            Demo preview PIN: <code className="bg-muted px-1 rounded">1234</code>
                        </span>
                    </div>

                    <div className="flex justify-end gap-2 pt-2">
                        <Button type="button" variant="outline" size="sm" onClick={onClose}>
                            Cancel
                        </Button>
                        <Button type="submit" size="sm" disabled={pin.length < 4}>
                            Unlock Message
                        </Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}

// ============================================================
// 3. Report Message Modal (Moderation Lite)
// ============================================================

interface ReportModalProps {
    open: boolean;
    messageId: number | null;
    snippet: string;
    onClose: () => void;
    onSubmit: (messageId: number, reason: string) => void;
}

export function ReportModal({ open, messageId, snippet, onClose, onSubmit }: ReportModalProps) {
    const [reason, setReason] = useState("Inappropriate / Offensive Language");
    const [comment, setComment] = useState("");

    if (!open || !messageId) return null;

    function handleReport(e: React.FormEvent) {
        e.preventDefault();
        const fullReason = comment.trim() ? `${reason} — Details: ${comment}` : reason;
        onSubmit(messageId!, fullReason);
        setComment("");
    }

    return (
        <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
            <DialogContent className="sm:max-w-[460px]">
                <DialogHeader>
                    <div className="flex items-center gap-2 text-rose-600">
                        <ShieldAlert className="h-5 w-5" />
                        <DialogTitle>Report Message to Principal 🔔</DialogTitle>
                    </div>
                </DialogHeader>

                <form onSubmit={handleReport} className="space-y-3 py-2 text-sm">
                    <div className="rounded border bg-rose-50/40 p-2.5 text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">Message excerpt:</span> &ldquo;{snippet}&rdquo;
                    </div>

                    <div>
                        <label className="text-xs font-medium text-foreground">Reason for Reporting</label>
                        <Select
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            className="mt-1"
                        >
                            <option value="Inappropriate / Offensive Language">Inappropriate / Offensive Language</option>
                            <option value="Harassment or Bullying">Harassment or Bullying</option>
                            <option value="Academic Dishonesty">Academic Dishonesty</option>
                            <option value="Spam or Unauthorized Solicitation">Spam or Unauthorized Solicitation</option>
                            <option value="Other Policy Violation">Other Policy Violation</option>
                        </Select>
                    </div>

                    <div>
                        <label className="text-xs font-medium text-foreground">Additional Notes (Optional)</label>
                        <Textarea
                            placeholder="Provide any additional context for the principal..."
                            value={comment}
                            onChange={(e) => setComment(e.target.value)}
                            rows={3}
                            className="mt-1 text-xs"
                        />
                    </div>

                    <p className="text-[11px] text-muted-foreground">
                        Submitting this form automatically logs a high-priority moderation ticket on the Principal&apos;s disciplinary oversight dashboard.
                    </p>

                    <div className="flex justify-end gap-2 pt-2">
                        <Button type="button" variant="outline" size="sm" onClick={onClose}>
                            Cancel
                        </Button>
                        <Button type="submit" variant="danger" size="sm">
                            Submit Disciplinary Report
                        </Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}

// ============================================================
// 4. Convert Chat to Ticket Modal
// ============================================================

interface ConvertTicketModalProps {
    open: boolean;
    messageId: number | null;
    snippet: string;
    onClose: () => void;
    onSubmit: (messageId: number, subject: string, category: string) => void;
}

export function ConvertTicketModal({
    open,
    messageId,
    snippet,
    onClose,
    onSubmit,
}: ConvertTicketModalProps) {
    const [subject, setSubject] = useState(() => (snippet ? snippet.slice(0, 60) : "Issue reported in chat"));
    const [category, setCategory] = useState("Facility");

    if (!open || !messageId) return null;

    function handleConvert(e: React.FormEvent) {
        e.preventDefault();
        onSubmit(messageId!, subject, category);
    }

    return (
        <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
            <DialogContent className="sm:max-w-120">
                <DialogHeader>
                    <div className="flex items-center gap-2 text-primary">
                        <AlertTriangle className="h-5 w-5 text-amber-500" />
                        <DialogTitle>Convert Chat to Support Ticket 🤖</DialogTitle>
                    </div>
                </DialogHeader>

                <form onSubmit={handleConvert} className="space-y-3 py-2 text-sm">
                    <p className="text-xs text-muted-foreground">
                        Our AI detected an issue or incident keyword. Turn this informal chat remark into a tracked, SLA-backed school ticket.
                    </p>

                    <div>
                        <label className="text-xs font-medium text-foreground">Ticket Title / Subject</label>
                        <Input
                            value={subject}
                            onChange={(e) => setSubject(e.target.value)}
                            className="mt-1"
                            required
                        />
                    </div>

                    <div>
                        <label className="text-xs font-medium text-foreground">Assignee Department</label>
                        <Select
                            value={category}
                            onChange={(e) => setCategory(e.target.value)}
                            className="mt-1"
                        >
                            <option value="IT">Tech Desk & IT Support</option>
                            <option value="Facility">Facility & Campus Maintenance</option>
                            <option value="Accounts">Finance & Fee Accounts</option>
                            <option value="Academic">Academic Committee</option>
                        </Select>
                    </div>

                    <div className="rounded border bg-muted/30 p-2.5 text-xs">
                        <span className="font-medium">Original Message:</span> &ldquo;{snippet}&rdquo;
                    </div>

                    <div className="flex justify-end gap-2 pt-2">
                        <Button type="button" variant="outline" size="sm" onClick={onClose}>
                            Keep as Chat
                        </Button>
                        <Button type="submit" size="sm">
                            Raise Formal Ticket
                        </Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}

interface NewChatModalProps {
    open: boolean;
    onClose: () => void;
    onSelectContact: (contact: ChatContact) => void;
    isStudentUser: boolean;
}

export function NewChatModal({
    open,
    onClose,
    onSelectContact,
}: NewChatModalProps) {
    const [search, setSearch] = useState("");
    const [contacts, setContacts] = useState<ChatContact[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!open) return;
        let alive = true;
        getChatContacts()
            .then((data) => {
                if (alive) {
                    setContacts(data);
                    setLoading(false);
                }
            })
            .catch(() => {
                if (alive) setLoading(false);
            });
        return () => {
            alive = false;
        };
    }, [open]);

    if (!open) return null;

    const filtered = contacts.filter((c) => {
        if (!search.trim()) return true;
        const q = search.toLowerCase();
        return (
            c.name.toLowerCase().includes(q) ||
            c.email.toLowerCase().includes(q) ||
            c.roleTag.toLowerCase().includes(q)
        );
    });

    const getRoleTone = (role: string): BadgeTone => {
        if (role === "admin") return "red";
        if (role === "principal") return "violet";
        if (role === "teacher") return "teal";
        if (role === "student") return "accent";
        if (role === "parent") return "amber";
        return "violet";
    };

    return (
        <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
            <DialogContent className="sm:max-w-[480px]">
                <DialogHeader>
                    <div className="flex items-center gap-2 text-primary">
                        <MessageSquarePlus className="h-5 w-5" />
                        <DialogTitle>Start New Conversation</DialogTitle>
                    </div>
                </DialogHeader>

                <div className="space-y-3 py-2">
                    <div className="rounded-lg border border-primary/20 bg-primary/5 p-2.5 text-xs text-primary flex items-start gap-2">
                        <UserCheck className="h-4 w-4 shrink-0 mt-0.5" />
                        <div>
                            <b>School Directory:</b> Select any verified school member or space to initiate a direct conversation.
                        </div>
                    </div>

                    <Input
                        placeholder="Search school members by name, email, or role..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        autoFocus
                    />

                    <div className="max-h-[280px] overflow-y-auto space-y-1.5 pr-1">
                        {loading ? (
                            <div className="py-8 flex justify-center">
                                <Spinner />
                            </div>
                        ) : filtered.length === 0 ? (
                            <div className="py-6 text-center text-xs text-muted-foreground">
                                No school members found matching &ldquo;{search}&rdquo;.
                            </div>
                        ) : (
                            filtered.map((contact) => (
                                <button
                                    key={`${contact.role}_${contact.id}`}
                                    type="button"
                                    onClick={() => onSelectContact(contact)}
                                    className="w-full flex items-center justify-between p-2.5 rounded-lg border text-left hover:bg-muted/50 transition-colors cursor-pointer group"
                                >
                                    <div className="flex items-center gap-2.5 min-w-0">
                                        <div
                                            className={`h-8 w-8 rounded-full flex items-center justify-center font-semibold text-xs shrink-0 ${
                                                contact.group
                                                    ? "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300"
                                                    : "bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-300"
                                            }`}
                                        >
                                            {contact.name.charAt(0)}
                                        </div>
                                        <div className="min-w-0">
                                            <div className="font-semibold text-xs text-foreground truncate group-hover:text-primary transition-colors">
                                                {contact.name}
                                            </div>
                                            <div className="text-[11px] text-muted-foreground truncate">
                                                {contact.email || contact.relationship}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="shrink-0 flex items-center gap-1.5 ml-2">
                                        <Badge tone={getRoleTone(contact.role)} className="text-[10px] capitalize">
                                            {contact.role}
                                        </Badge>
                                    </div>
                                </button>
                            ))
                        )}
                    </div>
                </div>

                <div className="flex justify-end pt-2">
                    <Button variant="outline" size="sm" onClick={onClose}>
                        Cancel
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
