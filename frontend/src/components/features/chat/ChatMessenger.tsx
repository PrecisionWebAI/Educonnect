"use client";

import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import {
    Input,
    Button,
    Badge,
    Spinner,
    type BadgeTone,
} from "@/components/ui";
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

    const isLockedAnnouncement =
        activeThread?.whoCanPost === "teachers_only" && isStudentUser;

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
            return { tone: "green" as BadgeTone, label: "Live Sync", icon: <Radio className="h-3 w-3 animate-pulse" /> };
        }
        if (socketStatus === "connecting") {
            return { tone: "amber" as BadgeTone, label: "Connecting...", icon: <Radio className="h-3 w-3 animate-spin" /> };
        }
        return { tone: "muted" as BadgeTone, label: "Local / Offline Mode", icon: null };
    }, [socketStatus]);

    return (
        <div className="flex flex-col lg:flex-row h-[calc(100vh-12rem)] min-h-[500px] border rounded-xl overflow-hidden bg-background shadow-xs">
            {/* ========================================================= */}
            {/* Left Pane: Thread List & Filters                          */}
            {/* ========================================================= */}
            <div className="w-full lg:w-80 xl:w-96 border-r flex flex-col h-full min-h-0 bg-muted/20 shrink-0 overflow-hidden">
                {/* Search & Actions Header */}
                <div className="p-3 border-b space-y-2 bg-card shrink-0">
                    <div className="flex items-center justify-between gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search conversations..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-8 h-9 text-xs"
                            />
                        </div>
                        <Button
                            size="sm"
                            variant="primary"
                            onClick={onOpenNewChatModal}
                            className="h-9 px-2.5 text-xs shrink-0"
                            title="New Conversation"
                        >
                            <UserPlus className="h-4 w-4 mr-1" />
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
                                    className={`px-2 py-1 rounded-md capitalize font-medium transition-colors ${
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
                            className="inline-flex items-center gap-1 cursor-pointer"
                            title="Click to reconnect WebSocket"
                        >
                            <Badge tone={socketBadge.tone} className="text-[10px] py-0 px-1.5 flex items-center gap-1">
                                {socketBadge.icon}
                                {socketBadge.label}
                            </Badge>
                        </button>
                    </div>
                </div>

                {/* Conversation Items List */}
                <div className="flex-1 min-h-0 chat-scroll-stream p-2 space-y-1">
                    {filteredConversations.length === 0 ? (
                        <div className="p-6 text-center text-xs text-muted-foreground">
                            No conversations match your search.
                        </div>
                    ) : (
                        filteredConversations.map((conv) => {
                            const isSelected = conv.id === selectedThreadId;
                            return (
                                <div
                                    key={conv.id}
                                    onClick={() => selectThread(conv.id)}
                                    className={`group relative flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-all border ${
                                        isSelected
                                            ? "bg-primary/10 border-primary/30 shadow-xs"
                                            : "border-transparent hover:bg-muted/60"
                                    }`}
                                >
                                    {/* Avatar */}
                                    <div className="relative shrink-0">
                                        <div
                                            className={`h-10 w-10 rounded-full flex items-center justify-center font-semibold text-sm ${
                                                conv.group
                                                    ? "bg-violet-100 text-violet-700"
                                                    : "bg-teal-100 text-teal-700"
                                            }`}
                                        >
                                            {conv.name.charAt(0)}
                                        </div>
                                        {conv.online && (
                                            <span className="absolute bottom-0 right-0 h-3 w-3 rounded-full bg-emerald-500 border-2 border-background" />
                                        )}
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between gap-1">
                                            <span className="font-semibold text-xs text-foreground truncate">
                                                {conv.name}
                                            </span>
                                            <span className="text-[10px] text-muted-foreground shrink-0">
                                                {conv.time}
                                            </span>
                                        </div>

                                        {conv.relationship && (
                                            <div className="text-[11px] text-primary/80 font-medium truncate">
                                                {conv.relationship}
                                            </div>
                                        )}

                                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                                            {conv.lastMessage}
                                        </p>
                                    </div>

                                    {/* Right Side Badges & Controls */}
                                    <div className="flex flex-col items-end justify-between shrink-0 self-stretch">
                                        <div className="flex items-center gap-1">
                                            {conv.pinned && (
                                                <Pin className="h-3 w-3 text-amber-500 fill-amber-500" />
                                            )}
                                            {conv.muted && (
                                                <BellOff className="h-3 w-3 text-muted-foreground" />
                                            )}
                                        </div>

                                        {conv.unread > 0 ? (
                                            <Badge tone="red" className="text-[10px] py-0 px-1.5 h-4 min-w-4 flex items-center justify-center rounded-full">
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
                <div className="p-2.5 border-t bg-card text-[11px] text-muted-foreground flex justify-between shrink-0">
                    <span>{conversations.length} total threads</span>
                    <span>{conversations.filter((c) => c.pinned).length} pinned</span>
                </div>
            </div>

            {/* ========================================================= */}
            {/* Right Pane: Active Thread Chat Stream & Compose           */}
            {/* ========================================================= */}
            <div className="flex-1 flex flex-col h-full min-h-0 bg-card overflow-hidden">
                {activeThread ? (
                    <>
                        {/* Conversation Header */}
                        <div className="p-3 border-b flex items-center justify-between bg-card z-10 shrink-0">
                            <div className="flex items-center gap-3">
                                <div
                                    className={`h-9 w-9 rounded-full flex items-center justify-center font-semibold text-xs ${
                                        activeThread.group
                                            ? "bg-violet-100 text-violet-700"
                                            : "bg-teal-100 text-teal-700"
                                    }`}
                                >
                                    {activeThread.name.charAt(0)}
                                </div>
                                <div>
                                    <div className="flex items-center gap-2">
                                        <span className="font-semibold text-sm text-foreground">
                                            {activeThread.name}
                                        </span>
                                        {activeThread.relationship && (
                                            <Badge tone="violet" className="text-[10px] py-0">
                                                {activeThread.relationship}
                                            </Badge>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        {activeThread.online ? (
                                            <span className="flex items-center gap-1 text-emerald-600 font-medium">
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
                                    className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
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
                                    className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                                    title={activeThread.muted ? "Unmute notifications" : "Mute notifications"}
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
                            <div className="bg-amber-50 dark:bg-amber-950/30 border-b border-amber-200 dark:border-amber-900/50 px-3 py-1.5 text-xs text-amber-800 dark:text-amber-300 flex items-center justify-between shrink-0">
                                <span className="flex items-center gap-1.5">
                                    <Shield className="h-3.5 w-3.5 shrink-0" />
                                    <b>Official Space:</b> High-importance notices broadcast to all members.
                                </span>
                                <Badge tone="amber" className="text-[10px]">Verified Channel</Badge>
                            </div>
                        )}

                        {/* Message Stream */}
                        <div ref={messagesContainerRef} className="flex-1 min-h-0 chat-scroll-stream p-4 space-y-3 bg-muted/10">
                            {messagesLoading ? (
                                <div className="flex items-center justify-center h-full">
                                    <Spinner />
                                </div>
                            ) : messages.length === 0 ? (
                                <div className="text-center py-16 text-muted-foreground text-xs">
                                    No messages in this conversation yet. Send a message below to start chatting!
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
                                                <div className="flex items-center gap-1.5 mb-1 px-1 text-[11px] text-muted-foreground font-medium">
                                                    <span>{m.senderName}</span>
                                                    {m.senderRole && (
                                                        <span className="text-[10px] bg-muted px-1.5 py-0.2 rounded">
                                                            {m.senderRole}
                                                        </span>
                                                    )}
                                                </div>
                                            )}

                                            {/* Main Message Bubble */}
                                            <div
                                                className={`group relative max-w-[85%] sm:max-w-[70%] p-3 rounded-2xl shadow-xs transition-all ${
                                                    m.isOfficial
                                                        ? "bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/40 dark:to-indigo-950/40 border border-blue-200 dark:border-blue-800 text-foreground"
                                                        : m.isMe
                                                          ? "bg-primary text-primary-foreground rounded-br-xs"
                                                          : "bg-card border text-card-foreground rounded-bl-xs"
                                                }`}
                                            >
                                                {/* Official Badge Shield */}
                                                {m.isOfficial && (
                                                    <div className="flex items-center gap-1 text-[11px] font-bold text-blue-600 dark:text-blue-400 mb-1 tracking-wide uppercase">
                                                        <Shield className="h-3.5 w-3.5 fill-blue-500 text-blue-500" />
                                                        Official School Announcement
                                                    </div>
                                                )}

                                                {/* Sensitive Information Lock */}
                                                {m.pinProtected && !m.unlocked ? (
                                                    <div className="flex items-center justify-between gap-3 p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 my-1">
                                                        <div className="flex items-center gap-2">
                                                            <Lock className="h-4 w-4 text-amber-500" />
                                                            <span className="text-xs font-semibold text-foreground">
                                                                Confidential Record (PIN Protected)
                                                            </span>
                                                        </div>
                                                        <Button
                                                            size="sm"
                                                            variant="outline"
                                                            className="h-7 text-xs"
                                                            onClick={() => onOpenPinModal(m.id)}
                                                        >
                                                            <Unlock className="h-3 w-3 mr-1" />
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
                                                    <div className="mt-2.5 p-2.5 rounded-xl border bg-background/80 flex items-center justify-between gap-2">
                                                        <div className="flex items-center gap-2 min-w-0">
                                                            {m.attachment.type === "pdf" ? (
                                                                <FileText className="h-5 w-5 text-rose-500 shrink-0" />
                                                            ) : m.attachment.type === "audio" ? (
                                                                <FileAudio className="h-5 w-5 text-amber-500 shrink-0" />
                                                            ) : (
                                                                <ExternalLink className="h-5 w-5 text-blue-500 shrink-0" />
                                                            )}
                                                            <div className="min-w-0">
                                                                <div className="text-xs font-semibold text-foreground truncate">
                                                                    {m.attachment.name}
                                                                </div>
                                                                <div className="text-[10px] text-muted-foreground">
                                                                    {m.attachment.size} • Safe Shield Verified
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <Button
                                                            size="sm"
                                                            variant="outline"
                                                            className="h-7 text-[11px] px-2 shrink-0"
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
                                                    <div className="mt-2 p-2 rounded-lg bg-amber-500/15 border border-amber-500/40 text-amber-900 dark:text-amber-200 text-xs flex items-center justify-between gap-2">
                                                        <div className="flex items-center gap-1.5">
                                                            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
                                                            <span>
                                                                🤖 <b>Issue detected:</b> Convert to tracked ticket?
                                                            </span>
                                                        </div>
                                                        <Button
                                                            size="sm"
                                                            variant="primary"
                                                            className="h-6 text-[10px] px-2"
                                                            onClick={() =>
                                                                onOpenTicketModal(m.id, m.text)
                                                            }
                                                        >
                                                            Convert to Ticket
                                                        </Button>
                                                    </div>
                                                )}

                                                {m.convertedTicketId && (
                                                    <div className="mt-2 text-[10px] font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
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
                                                        className="opacity-0 group-hover:opacity-100 absolute -right-7 top-2 p-1 text-muted-foreground hover:text-rose-600 transition-opacity"
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
                        <div className="p-3 border-t bg-card space-y-2 shrink-0">
                            {/* Quick Replies Chips */}
                            {!isLockedAnnouncement && (
                                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
                                    <Sparkles className="h-3.5 w-3.5 text-primary shrink-0 ml-1" />
                                    {QUICK_REPLIES.map((qr) => (
                                        <button
                                            key={qr}
                                            type="button"
                                            onClick={() => setInputText((prev) => (prev ? `${prev} ${qr}` : qr))}
                                            className="px-2.5 py-1 rounded-full border bg-muted/40 hover:bg-muted text-foreground text-xs whitespace-nowrap transition-colors cursor-pointer"
                                        >
                                            {qr}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {/* Active Attachment Pill */}
                            {selectedAttachment && (
                                <div className="flex items-center justify-between p-2 rounded-lg bg-primary/10 border border-primary/20 text-xs">
                                    <div className="flex items-center gap-2">
                                        <Paperclip className="h-3.5 w-3.5 text-primary" />
                                        <span className="font-semibold text-foreground">
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
                                <div className="p-1.5 rounded-md bg-rose-500/15 border border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-1.5">
                                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                                    <span>
                                        <b>Communication Advisory:</b> Sensitive wording detected. All school communications are logged and subject to conduct moderation.
                                    </span>
                                </div>
                            )}

                            {/* Compose Form */}
                            {isLockedAnnouncement ? (
                                <div className="p-3 text-center bg-muted/40 rounded-lg border text-xs text-muted-foreground">
                                    📢 This is a read-only announcement channel. Only assigned teachers and school administration can post updates.
                                </div>
                            ) : (
                                <form onSubmit={handleSend} className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        {/* Attachment Buttons */}
                                        <div className="flex items-center gap-1">
                                            <button
                                                type="button"
                                                onClick={() => attachMockFile("pdf")}
                                                className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground"
                                                title="Attach Document/PDF (25MB limit)"
                                            >
                                                <FileText className="h-4 w-4" />
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => attachMockFile("audio")}
                                                className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground"
                                                title="Attach Voice Note"
                                            >
                                                <FileAudio className="h-4 w-4" />
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => attachMockFile("link")}
                                                className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground"
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
                                            className="h-10 text-xs flex-1"
                                        />

                                        {/* Send Button */}
                                        <Button
                                            type="submit"
                                            disabled={submitting || (!inputText.trim() && !selectedAttachment)}
                                            size="sm"
                                            className="h-10 px-4"
                                        >
                                            <Send className="h-4 w-4 mr-1" />
                                            Send
                                        </Button>
                                    </div>

                                    {/* Quick Emoji Bar & Staff Controls */}
                                    <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                                        <div className="flex items-center gap-1">
                                            {EMOJIS.map((emoji) => (
                                                <button
                                                    key={emoji}
                                                    type="button"
                                                    onClick={() => setInputText((prev) => `${prev}${emoji}`)}
                                                    className="p-1 rounded hover:bg-muted text-sm"
                                                >
                                                    {emoji}
                                                </button>
                                            ))}
                                        </div>

                                        {canUseStaffFeatures && (
                                            <div className="flex items-center gap-3">
                                                <label className="flex items-center gap-1 cursor-pointer text-[11px]">
                                                    <input
                                                        type="checkbox"
                                                        checked={isOfficialNotice}
                                                        onChange={(e) => setIsOfficialNotice(e.target.checked)}
                                                        className="rounded text-primary focus:ring-0"
                                                    />
                                                    <Shield className="h-3 w-3 text-blue-500" />
                                                    Official Shield
                                                </label>
                                                <label className="flex items-center gap-1 cursor-pointer text-[11px]">
                                                    <input
                                                        type="checkbox"
                                                        checked={scheduledSend}
                                                        onChange={(e) => setScheduledSend(e.target.checked)}
                                                        className="rounded text-primary focus:ring-0"
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
                    <div className="flex flex-col items-center justify-center h-full p-8 text-center text-muted-foreground">
                        <p className="text-sm">Select a conversation from the left to start messaging.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
