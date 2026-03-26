'use client'

import { useState, useEffect, useCallback } from 'react'
import { api, type LDAPUser, GROUP_LABELS, GROUPS } from '@/lib/api'

type FormData = {
  username: string
  password: string
  first_name: string
  last_name: string
  email: string
  group: string
}

const INITIAL_FORM: FormData = {
  username: '', password: '', first_name: '', last_name: '', email: '', group: 'hostia',
}

export default function UsersPage() {
  const [users, setUsers] = useState<LDAPUser[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [groupFilter, setGroupFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<FormData>(INITIAL_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [editUser, setEditUser] = useState<LDAPUser | null>(null)
  const [changePassUser, setChangePassUser] = useState<string | null>(null)
  const [newPassword, setNewPassword] = useState('')

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
      await api.post('/users/', form)
      setShowCreate(false)
      setForm(INITIAL_FORM)
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
          {GROUPS.map((g) => (
            <option key={g} value={g}>{GROUP_LABELS[g]}</option>
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
                    {GROUP_LABELS[user.group] || user.group}
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
            <Field label="Meno (login)">
              <input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value.toLowerCase() })}
                className="input"
                placeholder="jan.novak"
              />
            </Field>
            <Field label="Heslo (min. 8 znakov)">
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="input"
              />
            </Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Meno">
                <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} className="input" />
              </Field>
              <Field label="Priezvisko">
                <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} className="input" />
              </Field>
            </div>
            <Field label="Email">
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="input" />
            </Field>
            <Field label="Skupina / VLAN">
              <select value={form.group} onChange={(e) => setForm({ ...form, group: e.target.value })} className="input">
                {GROUPS.map((g) => <option key={g} value={g}>{GROUP_LABELS[g]}</option>)}
              </select>
            </Field>
            <div className="flex gap-2 pt-2">
              <button onClick={createUser} disabled={saving} className="flex-1 bg-blue-600 text-white text-sm py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {saving ? 'Ukladám...' : 'Vytvoriť'}
              </button>
              <button onClick={() => { setShowCreate(false); setError('') }} className="px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                Zrušiť
              </button>
            </div>
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
