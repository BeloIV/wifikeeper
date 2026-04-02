'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'

const API_BASE = '/api'

type InvitationInfo = {
  email: string
  role: string
  expires_at: string
}

function formatRegistrationError(data: unknown): string {
  if (typeof data !== 'object' || data === null) return 'Chyba pri vytváraní účtu.'
  const d = data as Record<string, unknown>
  if (typeof d.detail === 'string') return d.detail
  const knownFields: Record<string, string> = {
    password: 'Heslo',
    first_name: 'Meno',
    last_name: 'Priezvisko',
  }
  const msgs = Object.keys(knownFields)
    .filter((k) => k in d)
    .map((k) => {
      const val = d[k]
      const errs = Array.isArray(val) ? val.map(String).join(' ') : String(val)
      return `${knownFields[k]}: ${errs}`
    })
  return msgs.length > 0 ? msgs.join(' ') : 'Chyba pri vytváraní účtu.'
}

const ROLE_LABELS: Record<string, string> = {
  superadmin: 'Superadmin',
  admin: 'Admin',
  readonly: 'Len čítanie',
}

export default function InvitePage() {
  const params = useParams()
  const router = useRouter()
  const token = params.token as string

  const [info, setInfo] = useState<InvitationInfo | null>(null)
  const [checkError, setCheckError] = useState('')
  const [checking, setChecking] = useState(true)

  const [form, setForm] = useState({ first_name: '', last_name: '', password: '', password2: '' })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (!/^[a-zA-Z0-9_-]{20,128}$/.test(token)) {
      setCheckError('Neplatná pozvánka.')
      setChecking(false)
      return
    }
    fetch(`${API_BASE}/admins/invitations/${token}/`)
      .then(async (res) => {
        if (res.status === 404) throw new Error('Pozvánka nenájdená.')
        if (res.status === 410) throw new Error('Pozvánka vypršala alebo bola už použitá.')
        if (!res.ok) throw new Error('Chyba servera.')
        return res.json()
      })
      .then((data) => setInfo(data))
      .catch((e) => setCheckError(e.message))
      .finally(() => setChecking(false))
  }, [token])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (form.password !== form.password2) {
      setFormError('Heslá sa nezhodujú.')
      return
    }
    setSaving(true)
    setFormError('')
    try {
      const res = await fetch(`${API_BASE}/admins/invitations/${token}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: form.first_name,
          last_name: form.last_name,
          password: form.password,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        setFormError(formatRegistrationError(data))
        return
      }
      setDone(true)
    } catch {
      setFormError('Chyba siete.')
    } finally {
      setSaving(false)
    }
  }

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-400 text-sm">Overujem pozvánku...</p>
      </div>
    )
  }

  if (checkError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-sm text-center space-y-4">
          <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mx-auto">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-gray-900">Neplatná pozvánka</h1>
          <p className="text-sm text-gray-500">{checkError}</p>
        </div>
      </div>
    )
  }

  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-sm text-center space-y-4">
          <div className="w-16 h-16 bg-green-100 rounded-2xl flex items-center justify-center mx-auto">
            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-gray-900">Účet vytvorený</h1>
          <p className="text-sm text-gray-500">Môžete sa prihlásiť do WiFi správcu.</p>
          <button
            onClick={() => router.push('/login')}
            className="w-full bg-blue-600 text-white font-medium py-2.5 px-4 rounded-lg text-sm hover:bg-blue-700"
          >
            Prihlásiť sa
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Registrácia</h1>
          <p className="text-sm text-gray-500 mt-1">WiFi Manager · Saleziánske oratórium</p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 mb-4 text-sm text-blue-800">
          <div>Pozvaný email: <strong>{info?.email}</strong></div>
          <div>Rola: <strong>{ROLE_LABELS[info?.role ?? ''] ?? info?.role}</strong></div>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
          {formError && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Meno</label>
              <input
                type="text"
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Ján"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Priezvisko</label>
              <input
                type="text"
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Novák"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Heslo * (min. 8 znakov)</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="••••••••"
              required
              minLength={8}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Zopakuj heslo *</label>
            <input
              type="password"
              value={form.password2}
              onChange={(e) => setForm({ ...form, password2: e.target.value })}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={saving || !form.password}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2.5 px-4 rounded-lg text-sm transition-colors"
          >
            {saving ? 'Vytváram účet...' : 'Vytvoriť účet'}
          </button>
          <p className="text-xs text-center text-gray-400">Prihlasovací email: {info?.email}</p>
        </form>
      </div>
    </div>
  )
}
