'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { api, type User, type AuditLog, ROLE_LABELS } from '@/lib/api'
import { formatDate } from '@/lib/utils'

export default function AdminsPage() {
  const router = useRouter()
  const [authorized, setAuthorized] = useState(false)
  const [admins, setAdmins] = useState<User[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'admins' | 'audit'>('admins')
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ email: '', role: 'admin' as User['role'] })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [inviteSent, setInviteSent] = useState(false)

  // Ochrana: len superadmin môže vidieť túto stránku
  useEffect(() => {
    api.get<User>('/admins/me/').then((u) => {
      if (u.role !== 'superadmin') {
        router.replace('/dashboard')
      } else {
        setAuthorized(true)
      }
    }).catch(() => router.replace('/login'))
  }, [router])

  const loadAdmins = useCallback(() => {
    api.get<{ results: User[] } | User[]>('/admins').then((d) => {
      setAdmins((d as { results: User[] }).results ?? (d as User[]))
    }).finally(() => setLoading(false))
  }, [])

  const loadAudit = useCallback(() => {
    api.get<{ results: AuditLog[] }>('/audit/').then((d) => setAuditLogs(d.results || []))
  }, [])

  useEffect(() => {
    if (tab === 'admins') loadAdmins()
    else loadAudit()
  }, [tab, loadAdmins, loadAudit])

  async function sendInvitation() {
    setSaving(true)
    setError('')
    try {
      await api.post('/admins/invitations/', form)
      setInviteSent(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Chyba')
    } finally {
      setSaving(false)
    }
  }

  function closeCreate() {
    setShowCreate(false)
    setError('')
    setInviteSent(false)
    setForm({ email: '', role: 'admin' })
  }

  async function deleteAdmin(id: number, username: string) {
    if (!confirm(`Zmazať admina ${username}?`)) return
    await api.delete(`/admins/${id}/`)
    loadAdmins()
  }

  if (!authorized) return null

  return (
    <div className="space-y-4 max-w-4xl">
      <h1 className="text-xl font-bold text-gray-900">Správa adminov</h1>

      {/* Taby */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab('admins')}
          className={`px-4 py-1.5 text-sm rounded-md font-medium transition-colors ${
            tab === 'admins' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
          }`}
        >
          Admini
        </button>
        <button
          onClick={() => setTab('audit')}
          className={`px-4 py-1.5 text-sm rounded-md font-medium transition-colors ${
            tab === 'audit' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
          }`}
        >
          Audit log
        </button>
      </div>

      {tab === 'admins' ? (
        <>
          <div className="flex justify-end">
            <button
              onClick={() => setShowCreate(true)}
              className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              + Nový admin
            </button>
          </div>

          <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
            {loading ? (
              <div className="p-8 text-center text-gray-400 text-sm">Načítavam...</div>
            ) : (
              <div className="divide-y divide-gray-50">
                {admins.map((admin) => (
                  <div key={admin.id} className="px-4 py-3 flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-sm font-medium text-gray-600 flex-shrink-0">
                      {(admin.first_name?.[0] || admin.username[0]).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm text-gray-900">{admin.username}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          admin.role === 'superadmin' ? 'bg-purple-100 text-purple-700' :
                          admin.role === 'admin' ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {ROLE_LABELS[admin.role]}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400">
                        {admin.email && `${admin.email} · `}
                        Posledné prihlásenie: {formatDate(admin.last_login ?? null)}
                      </div>
                    </div>
                    <button
                      onClick={() => deleteAdmin(admin.id, admin.username)}
                      className="text-xs px-2 py-1.5 rounded-lg text-red-400 hover:bg-red-50 flex-shrink-0"
                    >
                      🗑
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
          <div className="divide-y divide-gray-50">
            {auditLogs.length === 0 ? (
              <div className="p-8 text-center text-gray-400 text-sm">Žiadne záznamy</div>
            ) : auditLogs.map((log) => (
              <div key={log.id} className="px-4 py-2.5 flex items-start gap-3 text-sm">
                <span className="text-xs text-gray-300 flex-shrink-0 pt-0.5 w-32 text-right">
                  {formatDate(log.timestamp)}
                </span>
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-gray-700">{log.admin_user}</span>
                  <span className="text-gray-400 mx-1.5">·</span>
                  <span className="text-gray-600">{log.action}</span>
                  {log.target && (
                    <>
                      <span className="text-gray-400 mx-1.5">→</span>
                      <span className="text-gray-500 font-mono text-xs">{log.target}</span>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal – pozvánka admina */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/30">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-xl">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <h3 className="font-semibold text-gray-900">Pozvať admina</h3>
              <button onClick={closeCreate} className="text-gray-400 hover:text-gray-600 p-1">✕</button>
            </div>
            <div className="p-5 space-y-3">
              {inviteSent ? (
                <>
                  <div className="text-sm text-green-700 bg-green-50 border border-green-200 px-4 py-3 rounded-xl">
                    Pozvánka bola odoslaná na <strong>{form.email}</strong>. Odkaz je platný 7 dní.
                  </div>
                  <button onClick={closeCreate} className="w-full bg-blue-600 text-white text-sm py-2.5 rounded-lg hover:bg-blue-700">
                    Zavrieť
                  </button>
                </>
              ) : (
                <>
                  {error && <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</div>}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Email pozvaného</label>
                    <input
                      type="email"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      className="input"
                      placeholder="admin@priklad.sk"
                      autoFocus
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Rola</label>
                    <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as User['role'] })} className="input">
                      {Object.entries(ROLE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </select>
                  </div>
                  <p className="text-xs text-gray-400">
                    Pozvaný dostane email s odkazom na registráciu (platný 7 dní). Účet si vytvorí sám.
                  </p>
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={sendInvitation}
                      disabled={saving || !form.email}
                      className="flex-1 bg-blue-600 text-white text-sm py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                    >
                      {saving ? 'Odosielam...' : 'Odoslať pozvánku'}
                    </button>
                    <button onClick={closeCreate} className="px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                      Zrušiť
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
