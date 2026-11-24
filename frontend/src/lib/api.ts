/** Typed client for the AttendFX JSON API (/api). Same origin, cookie session, CSRF header. */

export type Role = 'student' | 'teacher' | 'admin'

export interface User {
  id: string
  name: string
  email: string
  role: Role
}

export interface Me {
  user: User
  csrf_token: string
  expires_at: string
}

export type KeyStatus = 'active' | 'expired' | 'revoked'

export interface AccessKey {
  id: string
  name: string
  prefix: string
  created_at: string
  last_used_at: string | null
  expires_at: string | null
  revoked_at: string | null
  status: KeyStatus
}

export interface KeyList {
  keys: AccessKey[]
  active: number
  max_active: number
  max_days: number
}

export interface IssuedKey {
  id: string
  key: string
  prefix: string
  name: string
  expires_at: string
}

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

let csrfToken: string | null = null

export function rememberCsrf(token: string | null) {
  csrfToken = token
}

async function request<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET' && csrfToken) headers['X-CSRF-Token'] = csrfToken

  let res: Response
  try {
    res = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'same-origin',
    })
  } catch {
    throw new ApiError(0, 'Could not reach AttendFX. Check your connection and try again.')
  }
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : null
    throw new ApiError(res.status, detail ?? `Something went wrong (${res.status}).`)
  }
  return data as T
}

export const api = {
  me: () => request<Me>('GET', '/api/me'),
  signIn: (email: string, password: string) =>
    request<Me>('POST', '/api/auth/sign-in', { email, password }),
  signOut: () => request<void>('POST', '/api/auth/sign-out'),
  keys: () => request<KeyList>('GET', '/api/keys'),
  createKey: (name: string, days: number) =>
    request<IssuedKey>('POST', '/api/keys', { name, days }),
  revokeKey: (id: string) => request<{ status: string }>('POST', `/api/keys/${id}/revoke`),
}
