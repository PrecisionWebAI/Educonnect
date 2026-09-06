"use client";

import { Tabs, Spinner, Badge } from "@/components/ui";
import { useChat, type ChatTab } from "./useChat";
import { ChatMessenger } from "./ChatMessenger";
import { GroupSpacesTab } from "./GroupSpacesTab";
import { InContextChatsTab } from "./InContextChatsTab";
import { ChatFilesTab } from "./ChatFilesTab";
import {
    SafeLinkModal,
    PinModal,
    ReportModal,
    ConvertTicketModal,
    NewChatModal,
} from "./ChatModals";
import { Radio } from "lucide-react";

const TABS: ChatTab[] = [
    "Conversations",
    "Group Spaces",
    "In-Context Chats",
    "Shared Files",
];

export default function ChatPage() {
    const c = useChat();

    return (
        <div className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                    <div className="flex items-center gap-2.5">
                        <span
                            aria-hidden="true"
                            className="h-6 w-1.5 shrink-0 rounded-full bg-primary"
                        />
                        <h1 className="text-2xl font-bold tracking-tight">Chat & Communication</h1>
                    </div>
                    <p className="text-muted-foreground text-xs mt-0.5">
                        Direct and group conversations with students, parents, and colleagues under verified school relationship rules.
                    </p>
                </div>
            </div>

            {/* Navigation Tabs */}
            <Tabs
                tabs={TABS}
                active={c.tab}
                onChange={(t) => c.setTab(t as ChatTab)}
            />

            {c.loading ? (
                <div className="py-16 flex justify-center">
                    <Spinner />
                </div>
            ) : (
                <>

            {/* Top Stat Tiles - shown on overview tabs (Group Spaces, In-Context, Files) */}
            {c.tab !== "Conversations" && (
                <div className="stat-tiles">
                    <div className="stat-tile">
                        <b>{c.conversations.length}</b>
                        <span>Conversations</span>
                    </div>
                    <div className="stat-tile">
                        <b>{c.unreadTotal}</b>
                        <span>Unread Messages</span>
                    </div>
                    <div className="stat-tile">
                        <b>{c.onlineCount}</b>
                        <span>Contacts Online</span>
                    </div>
                    <div className="stat-tile">
                        <div className="flex items-center gap-1.5">
                            {c.socketStatus === "connected" ? (
                                <>
                                    <Radio className="h-4 w-4 text-emerald-500 animate-pulse" />
                                    <b className="text-emerald-600 dark:text-emerald-400 text-sm">Live Sync</b>
                                </>
                            ) : c.socketStatus === "connecting" ? (
                                <>
                                    <Radio className="h-4 w-4 text-amber-500 animate-spin" />
                                    <b className="text-amber-600 dark:text-amber-400 text-sm">Connecting...</b>
                                </>
                            ) : (
                                <>
                                    <b className="text-muted-foreground text-sm">Offline Mode</b>
                                </>
                            )}
                        </div>
                        <span className="text-xs">
                            {c.socketStatus === "connected" ? (
                                <Badge tone="green" className="text-[10px]">WebSocket Active</Badge>
                            ) : (
                                <button
                                    type="button"
                                    onClick={c.reconnectSocket}
                                    className="text-[11px] text-primary hover:underline"
                                >
                                    Click to Reconnect
                                </button>
                            )}
                        </span>
                    </div>
                </div>
            )}

                    {/* Tab Views */}
                    {c.tab === "Conversations" && (
                        <ChatMessenger
                            conversations={c.conversations}
                            filteredConversations={c.filteredConversations}
                            activeThread={c.activeThread}
                            selectedThreadId={c.selectedThreadId}
                            selectThread={c.selectThread}
                            messages={c.messages}
                            messagesLoading={c.messagesLoading}
                            sendMessage={c.sendMessage}
                            togglePinThread={c.togglePinThread}
                            toggleMuteThread={c.toggleMuteThread}
                            socketStatus={c.socketStatus}
                            reconnectSocket={c.reconnectSocket}
                            searchQuery={c.searchQuery}
                            setSearchQuery={c.setSearchQuery}
                            filter={c.filter}
                            setFilter={c.setFilter}
                            onOpenSafeLink={(url, name) =>
                                c.setSafeLinkModal({ open: true, url, name })
                            }
                            onOpenPinModal={(messageId) =>
                                c.setPinModal({ open: true, messageId })
                            }
                            onOpenReportModal={(messageId, snippet) =>
                                c.setReportModal({ open: true, messageId, text: snippet })
                            }
                            onOpenTicketModal={(messageId, snippet) =>
                                c.setTicketModal({ open: true, messageId, text: snippet })
                            }
                            onOpenNewChatModal={() => c.setNewChatModalOpen(true)}
                            isStudentUser={c.isStudentUser}
                        />
                    )}

                    {c.tab === "Group Spaces" && (
                        <GroupSpacesTab onOpenSpaceChat={c.openEntityChat} />
                    )}

                    {c.tab === "In-Context Chats" && (
                        <InContextChatsTab onOpenEntityChat={c.openEntityChat} />
                    )}

                    {c.tab === "Shared Files" && (
                        <ChatFilesTab
                            onOpenSafeLink={(url, name) =>
                                c.setSafeLinkModal({ open: true, url, name })
                            }
                        />
                    )}

                    {/* Modals */}
                    <SafeLinkModal
                        open={c.safeLinkModal.open}
                        url={c.safeLinkModal.url}
                        name={c.safeLinkModal.name}
                        onClose={() =>
                            c.setSafeLinkModal({ open: false, url: "", name: "" })
                        }
                    />

                    <PinModal
                        open={c.pinModal.open}
                        messageId={c.pinModal.messageId}
                        onClose={() => c.setPinModal({ open: false, messageId: null })}
                        onUnlock={c.handleUnlockMessage}
                    />

                    <ReportModal
                        open={c.reportModal.open}
                        messageId={c.reportModal.messageId}
                        snippet={c.reportModal.text}
                        onClose={() =>
                            c.setReportModal({ open: false, messageId: null, text: "" })
                        }
                        onSubmit={c.handleReportSubmit}
                    />

                    <ConvertTicketModal
                        open={c.ticketModal.open}
                        messageId={c.ticketModal.messageId}
                        snippet={c.ticketModal.text}
                        onClose={() =>
                            c.setTicketModal({ open: false, messageId: null, text: "" })
                        }
                        onSubmit={c.handleConvertToTicket}
                    />

                    <NewChatModal
                        open={c.newChatModalOpen}
                        onClose={() => c.setNewChatModalOpen(false)}
                        onSelectContact={c.addNewConversation}
                        isStudentUser={c.isStudentUser}
                    />
                </>
            )}
        </div>
    );
}
