"use client";

import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { Input, Button, Badge, Spinner, type BadgeTone } from "@/components/ui";
import {
    Search,
    Pin,
    PinOff,
    Bell,
    BellOff,
    Send,
    Paperclip,
    FileText,
    FileAudio,
    ExternalLink,
    Shield,
    Lock,
    Unlock,
    Flag,
    AlertTriangle,
    Check,
    CheckCheck,
    Radio,
    Clock,
    Sparkles,
    UserPlus,
    X,
} from "lucide-react";
import type { ChatConversation, ChatMessageItem, ChatAttachment } from "@/types";
import { useAuth } from "@/providers/auth-context";
import { isStaff } from "@/lib/auth/rbac";

interface ChatMessengerProps {
    conversations: ChatConversation[];
    filteredConversations: ChatConversation[];
    activeThread: ChatConversation | null;
    selectedThreadId: number;
    selectThread: (threadId: number) => void;
    messages: ChatMessageItem[];
    messagesLoading: boolean;
    sendMessage: (text: string, attachment?: ChatAttachment, isOfficial?: boolean) => Promise<void>;
    togglePinThread: (threadId: number) => void;
    toggleMuteThread: (threadId: number) => void;
    socketStatus: "connected" | "connecting" | "disconnected";
    reconnectSocket: () => void;
    searchQuery: string;
    setSearchQuery: (q: string) => void;
    filter: "all" | "direct" | "groups" | "unread";
    setFilter: (f: "all" | "direct" | "groups" | "unread") => void;
    // Modals
    onOpenSafeLink: (url: string, name: string) => void;
    onOpenPinModal: (messageId: number) => void;
    onOpenReportModal: (messageId: number, snippet: string) => void;
    onOpenTicketModal: (messageId: number, snippet: string) => void;
    onOpenNewChatModal: () => void;
    isStudentUser: boolean;
}

const QUICK_REPLIES = [
    "Okay 👍",
    "Noted 📝",
    "Will review 🔍",
    "Please check attachment 📎",
    "Thank you! 🙏",
    "Understood",
    "Let's discuss in class 🏫",
];

const EMOJIS = ["👍", "❤️", "👏", "📝", "⏰", "📢", "🙌", "✅"];

const SENSITIVE_WORDS = ["idiot", "stupid", "hate", "shut up", "cheat", "worthless"];

export function ChatMessenger({
    conversations,
    filteredConversations,
    activeThread,
    selectedThreadId,
    selectThread,
    messages,
    messagesLoading,
    sendMessage,
    togglePinThread,
    toggleMuteThread,
    socketStatus,
    reconnectSocket,
    searchQuery,
    setSearchQuery,
    filter,
    setFilter,
    onOpenSafeLink,
    onOpenPinModal,
    onOpenReportModal,
    onOpenTicketModal,
    onOpenNewChatModal,
    isStudentUser,
}: ChatMessengerProps) {
    const { user } = useAuth();
    const canUseStaffFeatures = isStaff(user?.roles);

    const [inputText, setInputText] = useState("");
    const [selectedAttachment, setSelectedAttachment] = useState<ChatAttachment | null>(null);
    const [isOfficialNotice, setIsOfficialNotice] = useState(false);
    const [scheduledSend, setScheduledSend] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    const messagesContainerRef = useRef<HTMLDivElement | null>(null);
    const messagesEndRef = useRef<HTMLDivElement | null>(null);

    const scrollToBottom = useCallback((smooth = false) => {
        const el = messagesContainerRef.current;
        if (el) {
            requestAnimationFrame(() => {
                el.scrollTo({
                    top: el.scrollHeight,
                    behavior: smooth ? "smooth" : "auto",
                });
            });
        } else if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: smooth ? "smooth" : "auto" });
        }
    }, []);

    // Auto-scroll to bottom when messages update or thread loads
    useEffect(() => {
        if (!messagesLoading) {
            scrollToBottom(true);
        }
    }, [messages, messagesLoading, scrollToBottom]);

    // Fast instant scroll when user selects a different thread
    useEffect(() => {
        scrollToBottom(false);
    }, [selectedThreadId, scrollToBottom]);

    // Check for soft-censor words
    const detectedInappropriate = useMemo(() => {
        const lower = inputText.toLowerCase();
        return SENSITIVE_WORDS.some((word) => lower.includes(word));
    }, [inputText]);

    // Handle submit
    async function handleSend(e?: React.FormEvent) {
        if (e) e.preventDefault();
        const textToSend = inputText.trim();
        if (!textToSend && !selectedAttachment) return;

        setSubmitting(true);
        const finalNotice = isOfficialNotice && canUseStaffFeatures;
        try {
            await sendMessage(
                scheduledSend ? `[Scheduled for 08:00 AM Assembly] ${textToSend}` : textToSend,
                selectedAttachment || undefined,
                finalNotice,
            );
            setInputText("");
            setSelectedAttachment(null);
            setIsOfficialNotice(false);
            setScheduledSend(false);
            scrollToBottom(true);
        } finally {
            setSubmitting(false);
        }
    }

    const isLockedAnnouncement = activeThread?.whoCanPost === "teachers_only" && isStudentUser;

    // Attach mock files
    function attachMockFile(type: "pdf" | "image" | "audio" | "link") {
        if (type === "pdf") {
            setSelectedAttachment({
                name: "Class_Worksheet_Chapter5.pdf",
                type: "pdf",
                url: "https://educonnect.internal/files/Class_Worksheet_Chapter5.pdf",
                size: "2.3 MB",
                safeStatus: "verified",
            });
        } else if (type === "audio") {
            setSelectedAttachment({
                name: "Voice_Note_Instructions.mp3",
                type: "audio",
                url: "https://educonnect.internal/audio/voice-instructions.mp3",
                size: "1.1 MB",
                safeStatus: "verified",
            });
        } else if (type === "link") {
            setSelectedAttachment({
                name: "Physics_Simulations_Board.link",
                type: "link",
                url: "https://whiteboard.educonnect.internal/board/physics-sim",
                size: "Interactive",
                safeStatus: "verified",
            });
        } else {
            setSelectedAttachment({
                name: "Lab_Experiment_Diagram.png",
                type: "image",
                url: "https://educonnect.internal/images/lab-diagram.png",
                size: "3.4 MB",
                safeStatus: "verified",
            });
        }
    }

    // Socket status indicator config
    const socketBadge = useMemo(() => {
        if (socketStatus === "connected") {
            return {
                tone: "green" as BadgeTone,
                label: "Live Sync",
                icon: <Radio className="h-3 w-3 animate-pulse" />,
            };
        }
        if (socketStatus === "connecting") {
            return {
                tone: "amber" as BadgeTone,
                label: "Connecting...",
                icon: <Radio className="h-3 w-3 animate-spin" />,
            };
        }
        return { tone: "muted" as BadgeTone, label: "Local / Offline Mode", icon: null };
    }, [socketStatus]);

    return (
        <div className="bg-background flex h-[calc(100vh-12rem)] min-h-[500px] flex-col overflow-hidden rounded-xl border shadow-xs lg:flex-row">
            {/* ========================================================= */}
            {/* Left Pane: Thread List & Filters                          */}
            {/* ========================================================= */}
            <div className="bg-muted/20 flex h-full min-h-0 w-full shrink-0 flex-col overflow-hidden border-r lg:w-80 xl:w-96">
                {/* Search & Actions Header */}
                <div className="bg-card shrink-0 space-y-2 border-b p-3">
                    <div className="flex items-center justify-between gap-2">
                        <div className="relative flex-1">
                            <Search className="text-muted-foreground absolute top-2.5 left-2.5 h-4 w-4" />
                            <Input
                                placeholder="Search conversations..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="h-9 pl-8 text-xs"
                            />
                        </div>
                        <Button
                            size="sm"
                            variant="primary"
                            onClick={onOpenNewChatModal}
                            className="h-9 shrink-0 px-2.5 text-xs"
                            title="New Conversation"
                        >
                            <UserPlus className="mr-1 h-4 w-4" />
                            New
                        </Button>
                    </div>

                    {/* Filter Pills */}
                    <div className="flex items-center justify-between gap-1 text-xs">
                        <div className="flex items-center gap-1">
                            {(["all", "direct", "groups", "unread"] as const).map((f) => (
                                <button
                                    key={f}
                                    type="button"
                                    onClick={() => setFilter(f)}
                                    className={`rounded-md px-2 py-1 font-medium capitalize transition-colors ${
                                        filter === f
                                            ? "bg-primary text-primary-foreground"
                                            : "text-muted-foreground hover:bg-muted"
                                    }`}
                                >
                                    {f}
                                </button>
                            ))}
                        </div>

                        {/* Connection status pill */}
                        <button
                            type="button"
                            onClick={reconnectSocket}
                            className="inline-flex cursor-pointer items-center gap-1"
                            title="Click to reconnect WebSocket"
                        >
                            <Badge
                                tone={socketBadge.tone}
                                className="flex items-center gap-1 px-1.5 py-0 text-[10px]"
                            >
                                {socketBadge.icon}
                                {socketBadge.label}
                            </Badge>
                        </button>
                    </div>
                </div>

                {/* Conversation Items List */}
                <div className="chat-scroll-stream min-h-0 flex-1 space-y-1 p-2">
                    {filteredConversations.length === 0 ? (
                        <div className="text-muted-foreground p-6 text-center text-xs">
                            No conversations match your search.
                        </div>
                    ) : (
                        filteredConversations.map((conv) => {
                            const isSelected = conv.id === selectedThreadId;
                            return (
                                <div
                                    key={conv.id}
                                    onClick={() => selectThread(conv.id)}
                                    className={`group relative flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-all ${
                                        isSelected
                                            ? "bg-primary/10 border-primary/30 shadow-xs"
                                            : "hover:bg-muted/60 border-transparent"
                                    }`}
                                >
                                    {/* Avatar */}
                                    <div className="relative shrink-0">
                                        <div
                                            className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold ${
                                                conv.group
                                                    ? "bg-violet-100 text-violet-700"
                                                    : "bg-teal-100 text-teal-700"
                                            }`}
                                        >
                                            {conv.name.charAt(0)}
                                        </div>
                                        {conv.online && (
                                            <span className="border-background absolute right-0 bottom-0 h-3 w-3 rounded-full border-2 bg-emerald-500" />
                                        )}
                                    </div>

                                    {/* Content */}
                                    <div className="min-w-0 flex-1">
                                        <div className="flex items-center justify-between gap-1">
                                            <span className="text-foreground truncate text-xs font-semibold">
                                                {conv.name}
                                            </span>
                                            <span className="text-muted-foreground shrink-0 text-[10px]">
                                                {conv.time}
                                            </span>
                                        </div>

                                        {conv.relationship && (
                                            <div className="text-primary/80 truncate text-[11px] font-medium">
                                                {conv.relationship}
                                            </div>
                                        )}

                                        <p className="text-muted-foreground mt-0.5 truncate text-xs">
                                            {conv.lastMessage}
                                        </p>
                                    </div>

                                    {/* Right Side Badges & Controls */}
                                    <div className="flex shrink-0 flex-col items-end justify-between self-stretch">
                                        <div className="flex items-center gap-1">
                                            {conv.pinned && (
                                                <Pin className="h-3 w-3 fill-amber-500 text-amber-500" />
                                            )}
                                            {conv.muted && (
                                                <BellOff className="text-muted-foreground h-3 w-3" />
                                            )}
                                        </div>

                                        {conv.unread > 0 ? (
                                            <Badge
                                                tone="red"
                                                className="flex h-4 min-w-4 items-center justify-center rounded-full px-1.5 py-0 text-[10px]"
                                            >
                                                {conv.unread}
                                            </Badge>
                                        ) : (
                                            <CheckCheck className="h-3 w-3 text-sky-500" />
                                        )}
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>

                {/* Left pane footer stats */}
                <div className="bg-card text-muted-foreground flex shrink-0 justify-between border-t p-2.5 text-[11px]">
                    <span>{conversations.length} total threads</span>
                    <span>{conversations.filter((c) => c.pinned).length} pinned</span>
                </div>
            </div>

            {/* ========================================================= */}
            {/* Right Pane: Active Thread Chat Stream & Compose           */}
            {/* ========================================================= */}
            <div className="bg-card flex h-full min-h-0 flex-1 flex-col overflow-hidden">
                {activeThread ? (
                    <>
                        {/* Conversation Header */}
                        <div className="bg-card z-10 flex shrink-0 items-center justify-between border-b p-3">
                            <div className="flex items-center gap-3">
                                <div
                                    className={`flex h-9 w-9 items-center justify-center rounded-full text-xs font-semibold ${
                                        activeThread.group
                                            ? "bg-violet-100 text-violet-700"
                                            : "bg-teal-100 text-teal-700"
                                    }`}
                                >
                                    {activeThread.name.charAt(0)}
                                </div>
                                <div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-foreground text-sm font-semibold">
                                            {activeThread.name}
                                        </span>
                                        {activeThread.relationship && (
                                            <Badge tone="violet" className="py-0 text-[10px]">
                                                {activeThread.relationship}
                                            </Badge>
                                        )}
                                    </div>
                                    <div className="text-muted-foreground flex items-center gap-2 text-xs">
                                        {activeThread.online ? (
                                            <span className="flex items-center gap-1 font-medium text-emerald-600">
                                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                                                Active now
                                            </span>
                                        ) : (
                                            <span>Offline</span>
                                        )}
                                        {activeThread.whoCanPost === "teachers_only" && (
                                            <span>• 📢 Teachers Only Announcement Space</span>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Actions on Header */}
                            <div className="flex items-center gap-1">
                                <button
                                    type="button"
                                    onClick={() => togglePinThread(activeThread.id)}
                                    className="hover:bg-muted text-muted-foreground hover:text-foreground rounded-md p-1.5 transition-colors"
                                    title={activeThread.pinned ? "Unpin thread" : "Pin thread"}
                                >
                                    {activeThread.pinned ? (
                                        <PinOff className="h-4 w-4 text-amber-500" />
                                    ) : (
                                        <Pin className="h-4 w-4" />
                                    )}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => toggleMuteThread(activeThread.id)}
                                    className="hover:bg-muted text-muted-foreground hover:text-foreground rounded-md p-1.5 transition-colors"
                                    title={
                                        activeThread.muted
                                            ? "Unmute notifications"
                                            : "Mute notifications"
                                    }
                                >
                                    {activeThread.muted ? (
                                        <Bell className="h-4 w-4 text-amber-500" />
                                    ) : (
                                        <BellOff className="h-4 w-4" />
                                    )}
                                </button>
                            </div>
                        </div>

                        {/* Announcement / Pinned Notice Banner */}
                        {activeThread.isAnnouncementChannel && (
                            <div className="flex shrink-0 items-center justify-between border-b border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300">
                                <span className="flex items-center gap-1.5">
                                    <Shield className="h-3.5 w-3.5 shrink-0" />
                                    <b>Official Space:</b> High-importance notices broadcast to all
                                    members.
                                </span>
                                <Badge tone="amber" className="text-[10px]">
                                    Verified Channel
                                </Badge>
                            </div>
                        )}

                        {/* Message Stream */}
                        <div
                            ref={messagesContainerRef}
                            className="chat-scroll-stream bg-muted/10 min-h-0 flex-1 space-y-3 p-4"
                        >
                            {messagesLoading ? (
                                <div className="flex h-full items-center justify-center">
                                    <Spinner />
                                </div>
                            ) : messages.length === 0 ? (
                                <div className="text-muted-foreground py-16 text-center text-xs">
                                    No messages in this conversation yet. Send a message below to
                                    start chatting!
                                </div>
                            ) : (
                                messages.map((m) => {
                                    return (
                                        <div
                                            key={m.id}
                                            className={`flex flex-col ${m.isMe ? "items-end" : "items-start"}`}
                                        >
                                            {/* Sender title if not me */}
                                            {!m.isMe && (
                                                <div className="text-muted-foreground mb-1 flex items-center gap-1.5 px-1 text-[11px] font-medium">
                                                    <span>{m.senderName}</span>
                                                    {m.senderRole && (
                                                        <span className="bg-muted py-0.2 rounded px-1.5 text-[10px]">
                                                            {m.senderRole}
                                                        </span>
                                                    )}
                                                </div>
                                            )}

                                            {/* Main Message Bubble */}
                                            <div
                                                className={`group relative max-w-[85%] rounded-2xl p-3 shadow-xs transition-all sm:max-w-[70%] ${
                                                    m.isOfficial
                                                        ? "text-foreground border border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50 dark:border-blue-800 dark:from-blue-950/40 dark:to-indigo-950/40"
                                                        : m.isMe
                                                          ? "bg-primary text-primary-foreground rounded-br-xs"
                                                          : "bg-card text-card-foreground rounded-bl-xs border"
                                                }`}
                                            >
                                                {/* Official Badge Shield */}
                                                {m.isOfficial && (
                                                    <div className="mb-1 flex items-center gap-1 text-[11px] font-bold tracking-wide text-blue-600 uppercase dark:text-blue-400">
                                                        <Shield className="h-3.5 w-3.5 fill-blue-500 text-blue-500" />
                                                        Official School Announcement
                                                    </div>
                                                )}

                                                {/* Sensitive Information Lock */}
                                                {m.pinProtected && !m.unlocked ? (
                                                    <div className="my-1 flex items-center justify-between gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2">
                                                        <div className="flex items-center gap-2">
                                                            <Lock className="h-4 w-4 text-amber-500" />
                                                            <span className="text-foreground text-xs font-semibold">
                                                                Confidential Record (PIN Protected)
                                                            </span>
                                                        </div>
                                                        <Button
                                                            size="sm"
                                                            variant="outline"
                                                            className="h-7 text-xs"
                                                            onClick={() => onOpenPinModal(m.id)}
                                                        >
                                                            <Unlock className="mr-1 h-3 w-3" />
                                                            Enter PIN
                                                        </Button>
                                                    </div>
                                                ) : (
                                                    <p className="text-xs leading-relaxed whitespace-pre-wrap">
                                                        {m.text}
                                                    </p>
                                                )}

                                                {/* Attachment Preview */}
                                                {m.attachment && (
                                                    <div className="bg-background/80 mt-2.5 flex items-center justify-between gap-2 rounded-xl border p-2.5">
                                                        <div className="flex min-w-0 items-center gap-2">
                                                            {m.attachment.type === "pdf" ? (
                                                                <FileText className="h-5 w-5 shrink-0 text-rose-500" />
                                                            ) : m.attachment.type === "audio" ? (
                                                                <FileAudio className="h-5 w-5 shrink-0 text-amber-500" />
                                                            ) : (
                                                                <ExternalLink className="h-5 w-5 shrink-0 text-blue-500" />
                                                            )}
                                                            <div className="min-w-0">
                                                                <div className="text-foreground truncate text-xs font-semibold">
                                                                    {m.attachment.name}
                                                                </div>
                                                                <div className="text-muted-foreground text-[10px]">
                                                                    {m.attachment.size} • Safe
                                                                    Shield Verified
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <Button
                                                            size="sm"
                                                            variant="outline"
                                                            className="h-7 shrink-0 px-2 text-[11px]"
                                                            onClick={() =>
                                                                onOpenSafeLink(
                                                                    m.attachment!.url,
                                                                    m.attachment!.name,
                                                                )
                                                            }
                                                        >
                                                            Open
                                                        </Button>
                                                    </div>
                                                )}

                                                {/* Smart Issue Detector Convert to Ticket Banner */}
                                                {m.hasIssueDetected && (
                                                    <div className="mt-2 flex items-center justify-between gap-2 rounded-lg border border-amber-500/40 bg-amber-500/15 p-2 text-xs text-amber-900 dark:text-amber-200">
                                                        <div className="flex items-center gap-1.5">
                                                            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
                                                            <span>
                                                                🤖 <b>Issue detected:</b> Convert to
                                                                tracked ticket?
                                                            </span>
                                                        </div>
                                                        <Button
                                                            size="sm"
                                                            variant="primary"
                                                            className="h-6 px-2 text-[10px]"
                                                            onClick={() =>
                                                                onOpenTicketModal(m.id, m.text)
                                                            }
                                                        >
                                                            Convert to Ticket
                                                        </Button>
                                                    </div>
                                                )}

                                                {m.convertedTicketId && (
                                                    <div className="mt-2 flex items-center gap-1 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                                                        <Check className="h-3 w-3" />
                                                        Converted to Ticket #{m.convertedTicketId}
                                                    </div>
                                                )}

                                                {/* Timestamp & Read receipts */}
                                                <div
                                                    className={`mt-1 flex items-center justify-end gap-1 text-[10px] ${
                                                        m.isMe
                                                            ? "text-primary-foreground/70"
                                                            : "text-muted-foreground"
                                                    }`}
                                                >
                                                    <span>{m.time}</span>
                                                    {m.isMe && (
                                                        <span>
                                                            {m.status === "sent" ? (
                                                                <Check className="h-3 w-3" />
                                                            ) : m.status === "delivered" ? (
                                                                <CheckCheck className="h-3 w-3" />
                                                            ) : (
                                                                <CheckCheck className="h-3 w-3 text-sky-400" />
                                                            )}
                                                        </span>
                                                    )}
                                                </div>

                                                {/* Hover actions menu: Report */}
                                                {!m.isMe && (
                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            onOpenReportModal(m.id, m.text)
                                                        }
                                                        className="text-muted-foreground absolute top-2 -right-7 p-1 opacity-0 transition-opacity group-hover:opacity-100 hover:text-rose-600"
                                                        title="Report inappropriate message to principal"
                                                    >
                                                        <Flag className="h-3.5 w-3.5" />
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })
                            )}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Compose Dock (Tab 17.2 Messaging Features) */}
                        <div className="bg-card shrink-0 space-y-2 border-t p-3">
                            {/* Quick Replies Chips */}
                            {!isLockedAnnouncement && (
                                <div className="no-scrollbar flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
                                    <Sparkles className="text-primary ml-1 h-3.5 w-3.5 shrink-0" />
                                    {QUICK_REPLIES.map((qr) => (
                                        <button
                                            key={qr}
                                            type="button"
                                            onClick={() =>
                                                setInputText((prev) =>
                                                    prev ? `${prev} ${qr}` : qr,
                                                )
                                            }
                                            className="bg-muted/40 hover:bg-muted text-foreground cursor-pointer rounded-full border px-2.5 py-1 text-xs whitespace-nowrap transition-colors"
                                        >
                                            {qr}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {/* Active Attachment Pill */}
                            {selectedAttachment && (
                                <div className="bg-primary/10 border-primary/20 flex items-center justify-between rounded-lg border p-2 text-xs">
                                    <div className="flex items-center gap-2">
                                        <Paperclip className="text-primary h-3.5 w-3.5" />
                                        <span className="text-foreground font-semibold">
                                            {selectedAttachment.name}
                                        </span>
                                        <span className="text-muted-foreground text-[10px]">
                                            ({selectedAttachment.size})
                                        </span>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => setSelectedAttachment(null)}
                                        className="text-muted-foreground hover:text-foreground"
                                    >
                                        <X className="h-3.5 w-3.5" />
                                    </button>
                                </div>
                            )}

                            {/* Soft-censor warning banner */}
                            {detectedInappropriate && (
                                <div className="flex items-center gap-1.5 rounded-md border border-rose-500/30 bg-rose-500/15 p-1.5 text-xs text-rose-700 dark:text-rose-300">
                                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                                    <span>
                                        <b>Communication Advisory:</b> Sensitive wording detected.
                                        All school communications are logged and subject to conduct
                                        moderation.
                                    </span>
                                </div>
                            )}

                            {/* Compose Form */}
                            {isLockedAnnouncement ? (
                                <div className="bg-muted/40 text-muted-foreground rounded-lg border p-3 text-center text-xs">
                                    📢 This is a read-only announcement channel. Only assigned
                                    teachers and school administration can post updates.
                                </div>
                            ) : (
                                <form onSubmit={handleSend} className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        {/* Attachment Buttons */}
                                        <div className="flex items-center gap-1">
                                            <button
                                                type="button"
                                                onClick={() => attachMockFile("pdf")}
                                                className="hover:bg-muted text-muted-foreground hover:text-foreground rounded-lg p-2"
                                                title="Attach Document/PDF (25MB limit)"
                                            >
                                                <FileText className="h-4 w-4" />
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => attachMockFile("audio")}
                                                className="hover:bg-muted text-muted-foreground hover:text-foreground rounded-lg p-2"
                                                title="Attach Voice Note"
                                            >
                                                <FileAudio className="h-4 w-4" />
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => attachMockFile("link")}
                                                className="hover:bg-muted text-muted-foreground hover:text-foreground rounded-lg p-2"
                                                title="Attach Interactive Whiteboard Link"
                                            >
                                                <ExternalLink className="h-4 w-4" />
                                            </button>
                                        </div>

                                        {/* Main Input */}
                                        <Input
                                            placeholder="Type a message or select quick reply..."
                                            value={inputText}
                                            onChange={(e) => setInputText(e.target.value)}
                                            className="h-10 flex-1 text-xs"
                                        />

                                        {/* Send Button */}
                                        <Button
                                            type="submit"
                                            disabled={
                                                submitting ||
                                                (!inputText.trim() && !selectedAttachment)
                                            }
                                            size="sm"
                                            className="h-10 px-4"
                                        >
                                            <Send className="mr-1 h-4 w-4" />
                                            Send
                                        </Button>
                                    </div>

                                    {/* Quick Emoji Bar & Staff Controls */}
                                    <div className="text-muted-foreground flex items-center justify-between pt-1 text-xs">
                                        <div className="flex items-center gap-1">
                                            {EMOJIS.map((emoji) => (
                                                <button
                                                    key={emoji}
                                                    type="button"
                                                    onClick={() =>
                                                        setInputText((prev) => `${prev}${emoji}`)
                                                    }
                                                    className="hover:bg-muted rounded p-1 text-sm"
                                                >
                                                    {emoji}
                                                </button>
                                            ))}
                                        </div>

                                        {canUseStaffFeatures && (
                                            <div className="flex items-center gap-3">
                                                <label className="flex cursor-pointer items-center gap-1 text-[11px]">
                                                    <input
                                                        type="checkbox"
                                                        checked={isOfficialNotice}
                                                        onChange={(e) =>
                                                            setIsOfficialNotice(e.target.checked)
                                                        }
                                                        className="text-primary rounded focus:ring-0"
                                                    />
                                                    <Shield className="h-3 w-3 text-blue-500" />
                                                    Official Shield
                                                </label>
                                                <label className="flex cursor-pointer items-center gap-1 text-[11px]">
                                                    <input
                                                        type="checkbox"
                                                        checked={scheduledSend}
                                                        onChange={(e) =>
                                                            setScheduledSend(e.target.checked)
                                                        }
                                                        className="text-primary rounded focus:ring-0"
                                                    />
                                                    <Clock className="h-3 w-3 text-amber-500" />
                                                    Schedule (8:00 AM)
                                                </label>
                                            </div>
                                        )}
                                    </div>
                                </form>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="text-muted-foreground flex h-full flex-col items-center justify-center p-8 text-center">
                        <p className="text-sm">
                            Select a conversation from the left to start messaging.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
