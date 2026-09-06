import { api } from "@/lib/api/client";
import type {
    ChatConversation,
    ChatContact,
    ChatMessageItem,
    ChatFile,
    GroupSpace,
    InContextEntity,
    ClassNotice,
} from "@/types";

export async function getChatConversations(): Promise<ChatConversation[]> {
    try {
        const backendThreads = await api.get<
            Array<{ id: number; name?: string; is_group: boolean }>
        >("/chat/threads");
        if (Array.isArray(backendThreads)) {
            return backendThreads.map((t) => ({
                id: t.id,
                name: t.name || (t.is_group ? `Group #${t.id}` : `Chat #${t.id}`),
                group: t.is_group,
                lastMessage: "No recent messages",
                time: "Just now",
                unread: 0,
                online: true,
                relationship: t.is_group ? "Class Space" : "Colleague",
            }));
        }
    } catch (err) {
        console.error("Failed to fetch conversations", err);
    }
    return [];
}

export async function getChatMessages(threadId: number, currentUserId?: number): Promise<ChatMessageItem[]> {
    try {
        const backendMsgs = await api.get<
            Array<{
                id: number;
                thread_id: number;
                sender_id: number;
                sender_name?: string | null;
                sender_role?: string | null;
                content_text: string;
                attachment_url?: string | null;
                created_at?: string;
            }>
        >(`/chat/threads/${threadId}/messages`);

        if (Array.isArray(backendMsgs)) {
            return backendMsgs.map((m) => {
                const isMe = currentUserId ? m.sender_id === currentUserId : false;
                return {
                    id: m.id,
                    threadId: m.thread_id,
                    senderId: m.sender_id,
                    senderName: isMe ? "Me" : (m.sender_name || `User #${m.sender_id}`),
                    senderRole: m.sender_role || undefined,
                    isMe,
                    text: m.content_text,
                    time: m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Just now",
                    createdAt: m.created_at || new Date().toISOString(),
                    status: "read",
                    attachment: m.attachment_url
                        ? {
                              name: m.attachment_url.split("/").pop() || "Attachment",
                              type: m.attachment_url.endsWith(".pdf")
                                  ? "pdf"
                                  : m.attachment_url.endsWith(".mp3")
                                    ? "audio"
                                    : "link",
                              url: m.attachment_url,
                              size: "Unknown",
                              safeStatus: "verified",
                          }
                        : undefined,
                };
            });
        }
    } catch (err) {
        console.error("Failed to fetch messages", err);
    }
    return [];
}

export async function sendChatMessage(
    threadId: number,
    text: string,
    attachment?: ChatMessageItem["attachment"],
    isOfficial?: boolean,
): Promise<ChatMessageItem> {
    try {
        const res = await api.post<{
            id: number;
            thread_id: number;
            sender_id: number;
            content_text: string;
            attachment_url?: string | null;
            created_at?: string;
        }>(`/chat/threads/${threadId}/messages`, {
            content_text: text,
            attachment_url: attachment?.url || null,
        });

        return {
            id: res.id,
            threadId: res.thread_id,
            senderId: res.sender_id,
            senderName: "Me",
            isMe: true,
            text: res.content_text,
            time: res.created_at ? new Date(res.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            createdAt: res.created_at || new Date().toISOString(),
            status: "delivered",
            isOfficial: isOfficial ?? false,
            attachment,
        };
    } catch (err) {
        console.error("Failed to send message", err);
        throw err;
    }
}

export async function getGroupSpaces(): Promise<GroupSpace[]> {
    return [];
}

export async function getInContextEntities(): Promise<InContextEntity[]> {
    return [];
}

export async function getClassNotices(): Promise<ClassNotice[]> {
    return [];
}

export async function createClassNotice(notice: Partial<ClassNotice>): Promise<ClassNotice> {
    const created: ClassNotice = {
        id: Date.now(),
        title: notice.title || "New Class Notice",
        content: notice.content || "",
        pinnedBy: notice.pinnedBy || "Teacher",
        targetClass: notice.targetClass || "Class 10-A",
        createdAt: "Just now",
        priority: notice.priority || "Normal",
    };
    return created;
}

export async function reportChatMessage(
    messageId: number,
    reason: string,
): Promise<{ ticketId: number; message: string }> {
    const ticketId = Math.floor(1000 + Math.random() * 9000);
    return {
        ticketId,
        message: `Moderation report #${ticketId} submitted to Principal. Reason: ${reason}`,
    };
}

export async function convertChatToTicket(
    messageId: number,
    subject: string,
    category: string,
): Promise<{ ticketId: number; message: string }> {
    const ticketId = Math.floor(2000 + Math.random() * 8000);
    return {
        ticketId,
        message: `Ticket #${ticketId} raised for "${subject}" (${category}). Assigned to support desk.`,
    };
}

export async function getChatFiles(): Promise<ChatFile[]> {
    return [];
}

export async function getChatContacts(): Promise<ChatContact[]> {
    try {
        const backendContacts = await api.get<ChatContact[]>("/chat/contacts");
        if (Array.isArray(backendContacts)) {
            return backendContacts;
        }
    } catch (err) {
        console.error("Failed to fetch chat contacts", err);
    }
    return [];
}

export async function startConversationWithContact(
    contact: ChatContact,
): Promise<ChatConversation> {
    // If contact is an already existing group space
    if (contact.group && contact.threadId) {
        return {
            id: contact.threadId,
            name: contact.name,
            group: true,
            lastMessage: "No recent messages",
            time: "Just now",
            unread: 0,
            online: true,
            relationship: contact.relationship || "Class & Faculty Space",
        };
    }

    try {
        const createdThread = await api.post<{ id: number; name?: string; is_group: boolean }>(
            "/chat/threads",
            {
                name: contact.group ? contact.name : undefined,
                is_group: contact.group || false,
                participant_user_ids: [contact.id],
            }
        );

        return {
            id: createdThread.id,
            name: createdThread.name || contact.name,
            group: createdThread.is_group,
            lastMessage: "No recent messages",
            time: "Just now",
            unread: 0,
            online: true,
            relationship: contact.relationship || "Colleague",
        };
    } catch (err) {
        console.error("Failed to start conversation", err);
        throw err;
    }
}
