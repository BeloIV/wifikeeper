const BASE = '/api'

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    // Token expirovaný – presmeruj na login
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const msg = data.detail || data.message || `Chyba ${res.status}`
    throw new Error(msg)
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
  const data = await api.post<{
    access: string
    refresh: string
    user: User
  }>('/auth/login/', { username, password })
  localStorage.setItem('access_token', data.access)
  localStorage.setItem('refresh_token', data.refresh)
  return data.user
}

export function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
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
