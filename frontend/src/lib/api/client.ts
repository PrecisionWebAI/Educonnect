// ============================================================
// API client foundation — READY FOR BACKEND.
// Abhi kahin use nahi hota (pages @/db_demo se data le rahe hain).
// Backend wire hote hi services isi wrapper pe banenge aur
// db_demo/ delete ho jayega. Usage example:
//
//   const students = await apiGet<Student[]>('/api/v1/students')
//   await apiPost('/api/v1/students', { name: 'Aarav' })
// ============================================================

const API_BASE_URL =
  (process.env.NEXT_PUBLIC_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

const STORAGE_KEY = 'educonnect.session'

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as { accessToken?: string }).accessToken ?? null : null
  } catch {
    return null
  }
}

type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE'

async function request<T>(path: string, method: Method = 'GET', body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getAccessToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (!res.ok) {
    let message = `Request failed (${res.status})`
    try {
      const data = (await res.json()) as { detail?: unknown }
      if (typeof data.detail === 'string') message = data.detail
    } catch {
      /* non-JSON error body — generic message is fine */
    }
    throw new Error(message)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>(path, 'GET'),
  post: <T>(path: string, body?: unknown) => request<T>(path, 'POST', body),
  patch: <T>(path: string, body?: unknown) => request<T>(path, 'PATCH', body),
  delete: <T>(path: string) => request<T>(path, 'DELETE'),
}