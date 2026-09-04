// ============================================================
// API client foundation — EduConnect HTTP Client
// Communicates with FastAPI backend using NEXT_PUBLIC_API_BASE_URL.
// ============================================================

import { STORAGE_KEY } from "@/providers/auth-context";

const API_BASE_URL =
    (process.env.NEXT_PUBLIC_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

function getAccessToken(): string | null {
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

type Method = "GET" | "POST" | "PATCH" | "DELETE";

async function request<T>(path: string, method: Method = "GET", body?: unknown): Promise<T> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    const res = await fetch(`${API_BASE_URL}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
    });

    if (!res.ok) {
        let message = `Request failed (${res.status})`;
        try {
            const data = (await res.json()) as { detail?: unknown };
            if (typeof data.detail === "string") message = data.detail;
        } catch {
            /* non-JSON error body — generic message is fine */
        }
        throw new Error(message);
    }

    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
}

export const api = {
    get: <T>(path: string) => request<T>(path, "GET"),
    post: <T>(path: string, body?: unknown) => request<T>(path, "POST", body),
    patch: <T>(path: string, body?: unknown) => request<T>(path, "PATCH", body),
    delete: <T>(path: string) => request<T>(path, "DELETE"),
};
