'use client'

import { useState, useEffect, useCallback } from 'react'
import { api, type LDAPUser, type GroupInfo } from '@/lib/api'

type FormData = {
  first_name: string
  last_name: string
  email: string
  group: string
}

type CreatedUser = {
  username: string
  password: string
  email: string
}

const INITIAL_FORM: FormData = {
  first_name: '', last_name: '', email: '', group: '',
}

export default function UsersPage() {
  const [users, setUsers] = useState<LDAPUser[]>([])
  const [groups, setGroups] = useState<GroupInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [groupFilter, setGroupFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<FormData>(INITIAL_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [createdUser, setCreatedUser] = useState<CreatedUser | null>(null)
  const [changePassUser, setChangePassUser] = useState<string | null>(null)
  const [newPassword, setNewPassword] = useState('')

  useEffect(() => {
    api.get<GroupInfo[]>('/users/groups/').then((gs) => {
      setGroups(gs)
      setForm((f) => ({ ...f, group: f.group || gs[0]?.name || '' }))
    })
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    if (groupFilter) params.set('group', groupFilter)
    api.get<LDAPUser[]>(`/users/?${params}`).then(setUsers).finally(() => setLoading(false))
  }, [search, groupFilter])

  useEffect(() => { load() }, [load])

  async function createUser() {
    setSaving(true)
    setError('')
    try {
      const result = await api.post<CreatedUser>('/users/', form)
      setShowCreate(false)
      setForm({ ...INITIAL_FORM, group: groups[0]?.name || '' })
      setCreatedUser(result)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Chyba')
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(user: LDAPUser) {
    await api.post(`/users/${user.username}/activate/`, { active: user.disabled })
    load()
  }

  async function deleteUser(username: string) {
    if (!confirm(`Naozaj zmazať používateľa ${username}?`)) return
    await api.delete(`/users/${username}/`)
    load()
  }

  async function changePassword() {
    if (!changePassUser || newPassword.length < 8) return
    await api.post(`/users/${changePassUser}/password/`, { password: newPassword })
    setChangePassUser(null)
    setNewPassword('')
  }

  return (
    <div className="space-y-4 max-w-5xl">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-xl font-bold text-gray-900">Používatelia</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          + Nový používateľ
        </button>
      </div>

      {/* Filtre */}
      <div className="flex gap-2 flex-wrap">
        <input
          type="search"
          placeholder="Hľadať..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm flex-1 min-w-48 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={groupFilter}
          onChange={(e) => setGroupFilter(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Všetky skupiny</option>
          {groups.map((g) => (
            <option key={g.name} value={g.name}>{g.label}</option>
          ))}
        </select>
      </div>

      {/* Zoznam */}
      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Načítavam...</div>
        ) : users.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">Žiadni používatelia</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {users.map((user) => (
              <div key={user.username} className="px-4 py-3 flex items-center gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0 ${
                  user.disabled ? 'bg-gray-100 text-gray-400' : 'bg-blue-100 text-blue-700'
                }`}>
                  {(user.first_name?.[0] || user.username[0]).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm text-gray-900">{user.username}</span>
                    {user.disabled && (
                      <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">deaktivovaný</span>
                    )}
                  </div>
                  <div className="text-xs text-gray-400 truncate">
                    {user.full_name && `${user.full_name} · `}
                    {groups.find((g) => g.name === user.group)?.label || user.group}
                    {user.email && ` · ${user.email}`}
                  </div>
                </div>
                <div className="flex gap-1 flex-shrink-0">
                  <button
                    onClick={() => setChangePassUser(user.username)}
                    className="text-xs px-2 py-1.5 rounded-lg text-gray-500 hover:bg-gray-100"
                    title="Zmeniť heslo"
                  >
                    🔒
                  </button>
                  <button
                    onClick={() => toggleActive(user)}
                    className="text-xs px-2 py-1.5 rounded-lg text-gray-500 hover:bg-gray-100"
                    title={user.disabled ? 'Aktivovať' : 'Deaktivovať'}
                  >
                    {user.disabled ? '✅' : '🚫'}
                  </button>
                  <button
                    onClick={() => deleteUser(user.username)}
                    className="text-xs px-2 py-1.5 rounded-lg text-red-400 hover:bg-red-50"
                    title="Zmazať"
                  >
                    🗑
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal – vytvorenie */}
      {showCreate && (
        <Modal title="Nový používateľ" onClose={() => { setShowCreate(false); setError('') }}>
          <div className="space-y-3">
            {error && <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</div>}
            <div className="grid grid-cols-2 gap-2">
              <Field label="Meno *">
                <input
                  value={form.first_name}
                  onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                  className="input"
                  placeholder="Ján"
                />
              </Field>
              <Field label="Priezvisko *">
                <input
                  value={form.last_name}
                  onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                  className="input"
                  placeholder="Novák"
                />
              </Field>
            </div>
            <Field label="Email (voliteľný – login aj doručenie hesla)">
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="input"
                placeholder="jan@priklad.sk"
              />
            </Field>
            <Field label="Skupina / VLAN">
              <select value={form.group} onChange={(e) => setForm({ ...form, group: e.target.value })} className="input">
                {groups.map((g) => <option key={g.name} value={g.name}>{g.label} – VLAN {g.vlan}</option>)}
              </select>
            </Field>
            {!form.email && form.first_name && form.last_name && (
              <p className="text-xs text-gray-400">
                Login bude: <span className="font-mono text-gray-600">{slugify(form.first_name, form.last_name)}</span>
              </p>
            )}
            <div className="flex gap-2 pt-2">
              <button
                onClick={createUser}
                disabled={saving || !form.first_name || !form.last_name}
                className="flex-1 bg-blue-600 text-white text-sm py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Vytváram...' : 'Vytvoriť'}
              </button>
              <button onClick={() => { setShowCreate(false); setError('') }} className="px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                Zrušiť
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal – výsledok vytvorenia */}
      {createdUser && (
        <Modal title="Používateľ vytvorený" onClose={() => setCreatedUser(null)}>
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-sm text-green-700">
              Účet bol úspešne vytvorený.
              {createdUser.email && ' Prihlasovacie údaje boli odoslané emailom.'}
            </div>
            <div className="bg-gray-50 rounded-xl border border-gray-200 divide-y divide-gray-200 overflow-hidden">
              <div className="flex items-center px-4 py-3 gap-3">
                <span className="text-xs text-gray-400 w-16 flex-shrink-0">Login</span>
                <span className="font-mono text-sm text-gray-900 flex-1">{createdUser.username}</span>
                <button
                  onClick={() => navigator.clipboard.writeText(createdUser.username)}
                  className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100"
                >
                  Kopírovať
                </button>
              </div>
              <div className="flex items-center px-4 py-3 gap-3">
                <span className="text-xs text-gray-400 w-16 flex-shrink-0">Heslo</span>
                <span className="font-mono text-sm font-bold text-gray-900 flex-1 tracking-wider">{createdUser.password}</span>
                <button
                  onClick={() => navigator.clipboard.writeText(createdUser.password)}
                  className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100"
                >
                  Kopírovať
                </button>
              </div>
            </div>
            <button
              onClick={() => setCreatedUser(null)}
              className="w-full bg-blue-600 text-white text-sm py-2.5 rounded-lg hover:bg-blue-700"
            >
              Hotovo
            </button>
          </div>
        </Modal>
      )}

      {/* Modal – zmena hesla */}
      {changePassUser && (
        <Modal title={`Zmena hesla – ${changePassUser}`} onClose={() => { setChangePassUser(null); setNewPassword('') }}>
          <div className="space-y-3">
            <Field label="Nové heslo (min. 8 znakov)">
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="input"
                minLength={8}
              />
            </Field>
            <div className="flex gap-2 pt-2">
              <button
                onClick={changePassword}
                disabled={newPassword.length < 8}
                className="flex-1 bg-blue-600 text-white text-sm py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Zmeniť heslo
              </button>
              <button onClick={() => { setChangePassUser(null); setNewPassword('') }} className="px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                Zrušiť
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

function slugify(first: string, last: string): string {
  const str = `${first}.${last}`.toLowerCase()
  return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9.]/g, '')
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/30">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1">✕</button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  )
}
