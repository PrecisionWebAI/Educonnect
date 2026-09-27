// ============================================================
// API client foundation — EduConnect HTTP Client
// Communicates with FastAPI backend using NEXT_PUBLIC_API_BASE_URL.
// ============================================================

import { STORAGE_KEY } from "@/providers/auth-context";

const rawBase =
    (process.env.NEXT_PUBLIC_API_BASE_URL as string | undefined) ?? "http://localhost:8000";
const API_BASE_URL = rawBase.replace(/\/+$/, "");

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

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

/** The guard-failure body the backend sends: `{code, message}`. */
interface ApiErrorDetail {
    code?: unknown;
    message?: unknown;
}

/**
 * A failed request, with the HTTP status and the backend's machine code kept.
 *
 * `code` is what lets a screen speak for itself: the backend sends
 * `question_locked`, and the paper builder answers with "Access denied — this
 * question is locked", instead of leaking the raw API sentence to the teacher.
 */
export class ApiError extends Error {
    readonly status: number;
    readonly code?: string;

    constructor(message: string, status: number, code?: string) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.code = code;
    }

    /** True when the request never reached the backend (offline / server down). */
    get isNetworkError(): boolean {
        return this.status === 0;
    }
}

/**
 * Build an `ApiError` from a failed response.
 *
 * Two detail shapes exist across the API and both are handled here rather than
 * at each call site: a plain string (`detail: "Job 5 not found"`) and the
 * object form the question guards use (`detail: {code, message}`).
 */
async function toApiError(res: Response, fallback: string): Promise<ApiError> {
    let message = fallback;
    let code: string | undefined;
    try {
        const data = (await res.json()) as { detail?: unknown };
        const detail = data.detail;
        if (typeof detail === "string") {
            message = detail;
        } else if (detail && typeof detail === "object") {
            const shape = detail as ApiErrorDetail;
            if (typeof shape.message === "string") message = shape.message;
            if (typeof shape.code === "string") code = shape.code;
        }
    } catch {
        /* non-JSON error body — the generic message is fine */
    }
    return new ApiError(message, res.status, code);
}

/** Endpoints that are *allowed* to answer 401 without meaning "session over". */
const AUTH_PATHS = ["/auth/login", "/auth/token", "/auth/refresh"];

/**
 * The stored token expired — send the teacher back to sign in.
 *
 * The access token lives for 24 h and there is no refresh flow, so a 401 on an
 * app endpoint means the session is over. Without this the page still *looks*
 * signed in while every request silently fails. Clearing the session here, once
 * and centrally, is what makes "please sign in again" work on every screen.
 */
function handleExpiredSession(path: string): void {
    if (typeof window === "undefined") return;
    // Signing in with a wrong password is also a 401 — that is not an expiry.
    if (AUTH_PATHS.some((p) => path.startsWith(p))) return;

    try {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem("EduConnect.session");
        localStorage.removeItem("educonnect.session");
    } catch {
        /* storage unavailable — the redirect below still applies */
    }
    // Already on the sign-in screen: nothing to bounce.
    if (window.location.pathname.startsWith("/auth")) return;
    // A hard navigation on purpose: it also drops every cached query and piece
    // of in-memory state from the dead session, which a router.push() would keep.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/auth?expired=1";
}

async function request<T>(path: string, method: Method = "GET", body?: unknown): Promise<T> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    let res: Response;
    try {
        res = await fetch(`${API_BASE_URL}${path}`, {
            method,
            headers,
            body: body === undefined ? undefined : JSON.stringify(body),
        });
    } catch {
        // fetch() rejects only when the request never completed (server down,
        // offline, DNS). status 0 marks it so the UI can say "service
        // unavailable" rather than blaming the request itself.
        throw new ApiError("We could not reach the server.", 0);
    }

    if (!res.ok) {
        const err = await toApiError(res, `Request failed (${res.status})`);
        if (err.status === 401) handleExpiredSession(path);
        throw err;
    }

    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
}

/**
 * Multipart POST (file upload) — `Content-Type` **set nahi** karte: browser
 * khud boundary ke saath lagata hai. Isliye ye alag function hai, `request()`
 * nahi (jo har call par JSON header lagata hai).
 */
async function requestForm<T>(path: string, form: FormData): Promise<T> {
    const headers: Record<string, string> = {};
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    let res: Response;
    try {
        res = await fetch(`${API_BASE_URL}${path}`, {
            method: "POST",
            headers,
            body: form,
        });
    } catch {
        throw new ApiError("We could not reach the server.", 0);
    }

    if (!res.ok) {
        const err = await toApiError(res, `Request failed (${res.status})`);
        if (err.status === 401) handleExpiredSession(path);
        throw err;
    }

    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
}

export const api = {
    get: <T>(path: string) => request<T>(path, "GET"),
    post: <T>(path: string, body?: unknown) => request<T>(path, "POST", body),
    put: <T>(path: string, body?: unknown) => request<T>(path, "PUT", body),
    patch: <T>(path: string, body?: unknown) => request<T>(path, "PATCH", body),
    delete: <T>(path: string) => request<T>(path, "DELETE"),
    /** File upload (multipart) — source PDF/image ke liye (blueprint §2.9). */
    postForm: <T>(path: string, form: FormData) => requestForm<T>(path, form),
};
