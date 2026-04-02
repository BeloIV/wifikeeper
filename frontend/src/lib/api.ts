const BASE = '/api'

// ── Token refresh (singleton, aby nedošlo k súbežným refresh volaniam) ────────
let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  if (refreshPromise) return refreshPromise
  refreshPromise = fetch(`${BASE}/auth/refresh/`, {
    method: 'POST',
    credentials: 'include',
  })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => { refreshPromise = null })
  return refreshPromise
}

// ── Sanitizácia chybových správ ───────────────────────────────────────────────
function sanitizeError(data: Record<string, unknown>, status: number): string {
  if (typeof data.detail === 'string' && data.detail.length < 300) return data.detail
  if (typeof data.message === 'string' && data.message.length < 300) return data.message
  return `Chyba servera (${status}).`
}

// ── Základný request ──────────────────────────────────────────────────────────
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers, credentials: 'include' })

  if (res.status === 401) {
    const ok = await tryRefresh()
    if (ok) {
      const retry = await fetch(`${BASE}${path}`, { ...options, headers, credentials: 'include' })
      if (retry.status === 401) {
        window.location.href = '/login'
        throw new Error('Unauthorized')
      }
      if (!retry.ok) {
        const data = await retry.json().catch(() => ({}))
        throw new Error(sanitizeError(data, retry.status))
      }
      if (retry.status === 204) return undefined as T
      return retry.json()
    }
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(sanitizeError(data, res.status))
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function login(username: string, password: string) {
  const data = await request<{ user: User }>('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  return data.user
}

export async function logout() {
  await fetch(`${BASE}/auth/logout/`, { method: 'POST', credentials: 'include' }).catch(() => {})
  window.location.href = '/login'
}

// ── Types ─────────────────────────────────────────────────────────────────────
export type User = {
  id: number
  username: string
  first_name: string
  last_name: string
  email: string
  role: 'superadmin' | 'admin' | 'readonly'
  last_login?: string | null
}

export type LDAPUser = {
  username: string
  full_name: string
  first_name: string
  last_name: string
  email: string
  group: string
  disabled: boolean
}

export type TempKey = {
  id: string
  label: string
  key_type: 'one_time' | 'timed' | 'multi_use'
  ldap_username: string
  ldap_password?: string
  valid_hours: number | null
  expires_at: string | null
  used: boolean
  used_at: string | null
  max_uses: number | null
  use_count: number
  created_by: number | null
  created_by_name: string | null
  created_at: string
  email_sent_to: string
  ldap_deleted: boolean
  is_active: boolean
  is_expired: boolean
}

export type RadiusSession = {
  id: number
  acct_session_id: string
  username: string
  nas_ip_address: string
  nas_identifier: string
  called_station_id: string
  calling_station_id: string
  framed_ip_address: string | null
  acct_start_time: string | null
  acct_stop_time: string | null
  acct_session_time: number | null
  acct_terminate_cause: string
  connect_info_start: string
  is_active: boolean
  ssid: string
  ap_mac: string
  download_mb: number
  upload_mb: number
}

export type AuditLog = {
  id: number
  admin_user: string
  action: string
  target: string
  details: Record<string, unknown>
  ip_address: string | null
  timestamp: string
}

export type Group = string

export const ROLE_LABELS: Record<string, string> = {
  superadmin: 'Superadmin',
  admin: 'Admin',
  readonly: 'Len čítanie',
}

export type BulkUserResult = {
  index: number
  success: boolean
  email: string
  username?: string
  error?: string
}

export type BulkCreateResponse = {
  results: BulkUserResult[]
  created: number
  failed: number
}

export type GroupInfo = {
  name: string
  label: string
  vlan: number
  member_count: number
  members: LDAPUser[]
}
