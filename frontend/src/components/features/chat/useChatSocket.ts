"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { STORAGE_KEY } from "@/providers/auth-context";

export type SocketStatus = "connecting" | "connected" | "disconnected";

export interface WsIncomingMessage {
    id: number;
    thread_id: number;
    sender_id: number;
    sender_name?: string | null;
    sender_role?: string | null;
    content_text: string;
    attachment_url?: string | null;
    created_at?: string | null;
}

interface UseChatSocketOptions {
    onNewMessage?: (msg: WsIncomingMessage) => void;
    enabled?: boolean;
}

function getStoredToken(): string | null {
    if (typeof window === "undefined") return null;
    try {
        const raw =
            localStorage.getItem(STORAGE_KEY) ??
            localStorage.getItem("EduConnect.session") ??
            localStorage.getItem("educonnect.session");
        if (!raw) return null;
        const parsed = JSON.parse(raw) as { accessToken?: string; access_token?: string };
        return parsed.accessToken ?? parsed.access_token ?? null;
    } catch {
        return null;
    }
}

function getWebSocketUrl(token: string): string {
    const customWs = process.env.NEXT_PUBLIC_WS_BASE_URL;
    if (customWs) {
        return `${customWs.replace(/\/$/, "")}/chat/ws?token=${encodeURIComponent(token)}`;
    }

    const apiBase =
        (process.env.NEXT_PUBLIC_API_BASE_URL as string | undefined) ?? "http://localhost:8000";
    const wsBase = apiBase.replace(/^http/, "ws");
    return `${wsBase.replace(/\/$/, "")}/chat/ws?token=${encodeURIComponent(token)}`;
}

export function useChatSocket(options: UseChatSocketOptions = {}) {
    const { onNewMessage, enabled = true } = options;
    const [status, setStatus] = useState<SocketStatus>("disconnected");
    const [reconnectTrigger, setReconnectTrigger] = useState(0);
    const socketRef = useRef<WebSocket | null>(null);
    const reconnectAttemptsRef = useRef<number>(0);
    const onNewMessageRef = useRef(onNewMessage);

    useEffect(() => {
        onNewMessageRef.current = onNewMessage;
    }, [onNewMessage]);

    useEffect(() => {
        if (!enabled || typeof window === "undefined") return;

        const token = getStoredToken();
        if (!token) return;

        let isCancelled = false;
        let ws: WebSocket | null = null;
        let retryTimer: ReturnType<typeof setTimeout> | null = null;

        function doConnect() {
            if (isCancelled) return;
            const url = getWebSocketUrl(token!);

            try {
                ws = new WebSocket(url);
                socketRef.current = ws;

                ws.onopen = () => {
                    if (isCancelled) return;
                    setStatus("connected");
                    reconnectAttemptsRef.current = 0;
                };

                ws.onmessage = (event) => {
                    if (isCancelled) return;
                    try {
                        const data = JSON.parse(event.data);
                        if (data.event === "new_message" && data.message) {
                            onNewMessageRef.current?.(data.message as WsIncomingMessage);
                        }
                    } catch {
                        /* ignore non-JSON messages */
                    }
                };

                ws.onclose = () => {
                    if (isCancelled) return;
                    setStatus("disconnected");
                    socketRef.current = null;

                    if (reconnectAttemptsRef.current < 5) {
                        const delay = Math.min(1000 * 2 ** reconnectAttemptsRef.current, 15000);
                        reconnectAttemptsRef.current += 1;
                        retryTimer = setTimeout(doConnect, delay);
                    }
                };

                ws.onerror = () => {
                    if (isCancelled) return;
                    setStatus("disconnected");
                };
            } catch {
                /* ignore error on creation */
            }
        }

        doConnect();

        return () => {
            isCancelled = true;
            if (retryTimer) clearTimeout(retryTimer);
            if (ws) {
                try {
                    ws.close();
                } catch {
                    /* ignore */
                }
            }
            socketRef.current = null;
        };
    }, [enabled, reconnectTrigger]);

    const sendWsMessage = useCallback(
        (threadId: number, contentText: string, attachmentUrl?: string): boolean => {
            if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
                return false;
            }
            try {
                const payload = {
                    action: "send_message",
                    thread_id: threadId,
                    content_text: contentText,
                    attachment_url: attachmentUrl ?? null,
                };
                socketRef.current.send(JSON.stringify(payload));
                return true;
            } catch {
                return false;
            }
        },
        [],
    );

    const handleManualReconnect = useCallback(() => {
        reconnectAttemptsRef.current = 0;
        setReconnectTrigger((prev) => prev + 1);
    }, []);

    return {
        status,
        sendWsMessage,
        reconnect: handleManualReconnect,
    };
}
