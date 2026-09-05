"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
    getChatConversations,
    getChatMessages,
    sendChatMessage,
    reportChatMessage,
    convertChatToTicket,
    startConversationWithContact,
} from "@/services";
import type { ChatConversation, ChatContact, ChatMessageItem, ChatAttachment } from "@/types";
import { useChatSocket, type WsIncomingMessage } from "./useChatSocket";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { isStudent } from "@/lib/auth/rbac";

export type ChatTab = "Conversations" | "Group Spaces" | "In-Context Chats" | "Shared Files";
export type ThreadFilter = "all" | "direct" | "groups" | "unread";

export function useChat() {
    const { user } = useAuth();
    const { push } = useToast();
    const isStudentUser = isStudent(user?.roles);

    const [conversations, setConversations] = useState<ChatConversation[]>([]);
    const [loading, setLoading] = useState(true);
    const [tab, setTab] = useState<ChatTab>("Conversations");
    const [selectedThreadId, setSelectedThreadId] = useState<number>(1);
    const [messages, setMessages] = useState<ChatMessageItem[]>([]);
    const [messagesLoading, setMessagesLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [filter, setFilter] = useState<ThreadFilter>("all");

    // Modals state
    const [safeLinkModal, setSafeLinkModal] = useState<{
        open: boolean;
        url: string;
        name: string;
    }>({
        open: false,
        url: "",
        name: "",
    });
    const [pinModal, setPinModal] = useState<{ open: boolean; messageId: number | null }>({
        open: false,
        messageId: null,
    });
    const [reportModal, setReportModal] = useState<{
        open: boolean;
        messageId: number | null;
        text: string;
    }>({
        open: false,
        messageId: null,
        text: "",
    });
    const [ticketModal, setTicketModal] = useState<{
        open: boolean;
        messageId: number | null;
        text: string;
    }>({
        open: false,
        messageId: null,
        text: "",
    });
    const [newChatModalOpen, setNewChatModalOpen] = useState(false);

    // Initial conversations load
    useEffect(() => {
        let alive = true;
        getChatConversations().then((c) => {
            if (!alive) return;
            setConversations(c);
            setLoading(false);
            if (c.length > 0) {
                setSelectedThreadId((prev) => (prev ? prev : c[0].id));
            }
        });
        return () => {
            alive = false;
        };
    }, []);

    const currentUserId = user?.id;

    // Fetch messages for selected thread
    useEffect(() => {
        if (!selectedThreadId) return;
        let alive = true;
        getChatMessages(selectedThreadId, currentUserId)
            .then((msgs) => {
                if (!alive) return;
                setMessages(msgs);
                setMessagesLoading(false);
            })
            .catch(() => {
                if (!alive) return;
                setMessagesLoading(false);
            });
        return () => {
            alive = false;
        };
    }, [selectedThreadId, currentUserId]);

    // Real-time WebSocket event handler
    const handleWsNewMessage = useCallback(
        (wsMsg: WsIncomingMessage) => {
            if (wsMsg.thread_id === selectedThreadId) {
                setMessages((prev) => {
                    if (prev.some((m) => m.id === wsMsg.id)) return prev;
                    const isMe = currentUserId ? wsMsg.sender_id === currentUserId : false;
                    const newMsg: ChatMessageItem = {
                        id: wsMsg.id,
                        threadId: wsMsg.thread_id,
                        senderId: wsMsg.sender_id,
                        senderName: isMe ? "Me" : (wsMsg.sender_name || `User #${wsMsg.sender_id}`),
                        senderRole: wsMsg.sender_role || undefined,
                        isMe,
                        text: wsMsg.content_text,
                        time: "Just now",
                        createdAt: wsMsg.created_at || new Date().toISOString(),
                        status: "read",
                        attachment: wsMsg.attachment_url
                            ? {
                                  name: wsMsg.attachment_url.split("/").pop() || "Attachment",
                                  type: "link",
                                  url: wsMsg.attachment_url,
                                  size: "File",
                                  safeStatus: "verified",
                              }
                            : undefined,
                    };
                    return [...prev, newMsg];
                });
            }

            // Update thread's last message and bump unread if not active
            setConversations((prev) =>
                prev.map((c) => {
                    if (c.id === wsMsg.thread_id) {
                        return {
                            ...c,
                            lastMessage: wsMsg.content_text,
                            time: "Just now",
                            unread: c.id === selectedThreadId ? 0 : c.unread + 1,
                        };
                    }
                    return c;
                }),
            );
        },
        [selectedThreadId, currentUserId],
    );

    const { status: socketStatus, reconnect } = useChatSocket({
        onNewMessage: handleWsNewMessage,
    });

    const activeThread = useMemo(() => {
        return conversations.find((c) => c.id === selectedThreadId) ?? conversations[0] ?? null;
    }, [conversations, selectedThreadId]);

    // Filter conversations
    const filteredConversations = useMemo(() => {
        const q = searchQuery.toLowerCase().trim();
        return conversations.filter((c) => {
            if (filter === "direct" && c.group) return false;
            if (filter === "groups" && !c.group) return false;
            if (filter === "unread" && c.unread === 0) return false;
            if (!q) return true;
            return (
                c.name.toLowerCase().includes(q) ||
                c.lastMessage.toLowerCase().includes(q) ||
                (c.relationship && c.relationship.toLowerCase().includes(q))
            );
        });
    }, [conversations, filter, searchQuery]);

    // Send message action
    const sendMessage = useCallback(
        async (text: string, attachment?: ChatAttachment, isOfficial?: boolean) => {
            if (!selectedThreadId || (!text.trim() && !attachment)) return;

            // Check whoCanPost rules
            if (activeThread?.whoCanPost === "teachers_only" && isStudentUser) {
                push(
                    "error",
                    "This space is an announcement channel. Only teachers and staff can post.",
                );
                return;
            }

            // Persist via REST client and add to local state (avoid duplicate sendWsMessage)
            try {
                const saved = await sendChatMessage(selectedThreadId, text, attachment, isOfficial);
                setMessages((prev) => {
                    if (prev.some((m) => m.id === saved.id)) return prev;
                    return [...prev, saved];
                });
                setConversations((prev) =>
                    prev.map((c) =>
                        c.id === selectedThreadId
                            ? {
                                  ...c,
                                  lastMessage: text || (attachment ? attachment.name : ""),
                                  time: "Just now",
                              }
                            : c,
                    ),
                );
            } catch {
                push("error", "Failed to deliver message. Please try again.");
            }
        },
        [selectedThreadId, activeThread, isStudentUser, push],
    );

    // Pin/Unpin thread
    const togglePinThread = useCallback((threadId: number) => {
        setConversations((prev) =>
            prev.map((c) => (c.id === threadId ? { ...c, pinned: !c.pinned } : c)),
        );
    }, []);

    // Mute/Unmute thread
    const toggleMuteThread = useCallback((threadId: number) => {
        setConversations((prev) =>
            prev.map((c) => (c.id === threadId ? { ...c, muted: !c.muted } : c)),
        );
    }, []);

    // Select thread and mark unread as 0
    const selectThread = useCallback(
        (threadId: number) => {
            if (threadId === selectedThreadId) return;
            setMessagesLoading(true);
            setSelectedThreadId(threadId);
            setConversations((prev) => prev.map((c) => (c.id === threadId ? { ...c, unread: 0 } : c)));
        },
        [selectedThreadId],
    );

    // Jump from entity or space to conversation
    const openEntityChat = useCallback(
        (threadId: number) => {
            setTab("Conversations");
            if (threadId === selectedThreadId) return;
            setMessagesLoading(true);
            setSelectedThreadId(threadId);
            setConversations((prev) => prev.map((c) => (c.id === threadId ? { ...c, unread: 0 } : c)));
        },
        [selectedThreadId],
    );

    // PIN Unlock
    const handleUnlockMessage = useCallback(
        (messageId: number, pin: string) => {
            if (pin === "1234" || pin.length >= 4) {
                setMessages((prev) =>
                    prev.map((m) => (m.id === messageId ? { ...m, unlocked: true } : m)),
                );
                push("success", "Sensitive information unlocked successfully.");
                setPinModal({ open: false, messageId: null });
            } else {
                push("error", "Incorrect PIN code. Default preview PIN is 1234.");
            }
        },
        [push],
    );

    // Report message
    const handleReportSubmit = useCallback(
        async (messageId: number, reason: string) => {
            try {
                const res = await reportChatMessage(messageId, reason);
                setMessages((prev) =>
                    prev.map((m) => (m.id === messageId ? { ...m, reported: true } : m)),
                );
                push("success", res.message);
                setReportModal({ open: false, messageId: null, text: "" });
            } catch {
                push("error", "Could not submit report.");
            }
        },
        [push],
    );

    // Convert chat to ticket
    const handleConvertToTicket = useCallback(
        async (messageId: number, subject: string, category: string) => {
            try {
                const res = await convertChatToTicket(messageId, subject, category);
                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === messageId
                            ? { ...m, convertedTicketId: res.ticketId, hasIssueDetected: false }
                            : m,
                    ),
                );
                push("success", res.message);
                setTicketModal({ open: false, messageId: null, text: "" });
            } catch {
                push("error", "Could not create ticket.");
            }
        },
        [push],
    );

    // Add new thread or select existing one
    const addNewConversation = useCallback(
        async (contact: ChatContact) => {
            try {
                const conv = await startConversationWithContact(contact);
                setConversations((prev) => {
                    const idx = prev.findIndex((c) => c.id === conv.id);
                    if (idx >= 0) {
                        const updated = [...prev];
                        updated[idx] = conv;
                        return updated;
                    }
                    return [conv, ...prev];
                });
                setTab("Conversations");
                push("success", `Chat started with ${contact.name}.`);
                setNewChatModalOpen(false);

                if (conv.id === selectedThreadId) {
                    setMessagesLoading(true);
                    getChatMessages(conv.id, currentUserId)
                        .then((msgs) => setMessages(msgs))
                        .finally(() => setMessagesLoading(false));
                } else {
                    setMessagesLoading(true);
                    setSelectedThreadId(conv.id);
                }
            } catch {
                push("error", "Failed to start conversation.");
            }
        },
        [selectedThreadId, currentUserId, push],
    );

    const unreadTotal = useMemo(() => {
        return conversations.reduce((sum, c) => sum + c.unread, 0);
    }, [conversations]);

    const onlineCount = useMemo(() => {
        return conversations.filter((c) => c.online).length;
    }, [conversations]);

    return {
        tab,
        setTab,
        conversations,
        filteredConversations,
        activeThread,
        selectedThreadId,
        selectThread,
        openEntityChat,
        messages,
        messagesLoading,
        sendMessage,
        togglePinThread,
        toggleMuteThread,
        loading,
        unreadTotal,
        onlineCount,
        socketStatus,
        reconnectSocket: reconnect,
        searchQuery,
        setSearchQuery,
        filter,
        setFilter,
        // Modals
        safeLinkModal,
        setSafeLinkModal,
        pinModal,
        setPinModal,
        handleUnlockMessage,
        reportModal,
        setReportModal,
        handleReportSubmit,
        ticketModal,
        setTicketModal,
        handleConvertToTicket,
        newChatModalOpen,
        setNewChatModalOpen,
        addNewConversation,
        isStudentUser,
    };
}
