'use client'

import { useState, useEffect, useCallback } from 'react'
import { api, type TempKey } from '@/lib/api'
import { formatDate, formatRelative } from '@/lib/utils'

export default function KeysPage() {
  const [keys, setKeys] = useState<TempKey[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newKey, setNewKey] = useState<TempKey | null>(null)
  const [qr, setQr] = useState<{ qr_code: string; username: string } | null>(null)
  const [form, setForm] = useState({
    label: '',
    key_type: 'timed' as 'one_time' | 'timed',
    valid_hours: 24,
    email: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [activeOnly, setActiveOnly] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    const params = activeOnly ? '?active=1' : ''
    api.get<TempKey[]>(`/keys/${params}`).then(setKeys).finally(() => setLoading(false))
  }, [activeOnly])

  useEffect(() => { load() }, [load])

  async function createKey() {
    setSaving(true)
    setError('')
    try {
      const body: Record<string, unknown> = {
        label: form.label,
        key_type: form.key_type,
        email: form.email,
      }
      if (form.key_type === 'timed') body.valid_hours = form.valid_hours
      const created = await api.post<TempKey>('/keys/', body)
      setNewKey(created)
      setShowCreate(false)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Chyba')
    } finally {
      setSaving(false)
    }
  }

  async function deleteKey(id: string) {
    if (!confirm('Zmazať kľúč a LDAP účet?')) return
    await api.delete(`/keys/${id}/`)
    load()
  }

  async function showQR(id: string) {
    const data = await api.get<{ qr_code: string; username: string }>(`/keys/${id}/qr/`)
    setQr(data)
  }

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-xl font-bold text-gray-900">Dočasné kľúče</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          + Nový kľúč
        </button>
      </div>

      <label className="flex items-center gap-2 text-sm text-gray-600">
        <input
          type="checkbox"
          checked={activeOnly}
          onChange={(e) => setActiveOnly(e.target.checked)}
          className="rounded"
        />
        Len aktívne kľúče
      </label>

      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Načítavam...</div>
        ) : keys.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">Žiadne kľúče</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {keys.map((key) => (
              <div key={key.id} className="px-4 py-3">
                <div className="flex items-start gap-3">
                  <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                    key.is_active ? 'bg-green-400' : key.used ? 'bg-gray-300' : 'bg-red-400'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm text-gray-900">{key.ldap_username}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        key.key_type === 'one_time'
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {key.key_type === 'one_time' ? 'Jednorazový' : `${key.valid_hours}h`}
                      </span>
                      {key.used && <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">použitý</span>}
                      {key.is_expired && !key.used && <span className="text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded">expirovaný</span>}
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {key.label && `${key.label} · `}
                      Vytvorený {formatRelative(key.created_at)}
                      {key.expires_at && ` · Expiruje ${formatDate(key.expires_at)}`}
                      {key.email_sent_to && ` · Email: ${key.email_sent_to}`}
                    </div>
                  </div>
                  <div className="flex gap-1 flex-shrink-0">
                    <button onClick={() => showQR(key.id)} className="text-xs px-2 py-1.5 rounded-lg text-gray-500 hover:bg-gray-100" title="QR kód">
                      📷
                    </button>
                    <button onClick={() => deleteKey(key.id)} className="text-xs px-2 py-1.5 rounded-lg text-red-400 hover:bg-red-50" title="Zmazať">
                      🗑
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal – vytvorenie */}
      {showCreate && (
        <Modal title="Nový dočasný kľúč" onClose={() => { setShowCreate(false); setError('') }}>
          <div className="space-y-3">
            {error && <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</div>}
            <Field label="Popis / meno hosťa">
              <input
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
                className="input"
                placeholder="napr. Ján Novák – návšteva 22.3."
              />
            </Field>
            <Field label="Typ kľúča">
              <div className="grid grid-cols-2 gap-2">
                <label className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer ${
                  form.key_type === 'one_time' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                }`}>
                  <input
                    type="radio"
                    value="one_time"
                    checked={form.key_type === 'one_time'}
                    onChange={() => setForm({ ...form, key_type: 'one_time' })}
                    className="sr-only"
                  />
                  <div>
                    <div className="text-sm font-medium">Jednorazový</div>
                    <div className="text-xs text-gray-400">1 prihlásenie</div>
                  </div>
                </label>
                <label className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer ${
                  form.key_type === 'timed' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                }`}>
                  <input
                    type="radio"
                    value="timed"
                    checked={form.key_type === 'timed'}
                    onChange={() => setForm({ ...form, key_type: 'timed' })}
                    className="sr-only"
                  />
                  <div>
                    <div className="text-sm font-medium">Časový</div>
                    <div className="text-xs text-gray-400">N hodín</div>
                  </div>
                </label>
              </div>
            </Field>
            {form.key_type === 'timed' && (
              <Field label="Platnosť (hodiny)">
                <div className="flex gap-2">
                  {[2, 8, 24, 48, 168].map((h) => (
                    <button
                      key={h}
                      onClick={() => setForm({ ...form, valid_hours: h })}
                      className={`flex-1 py-1.5 text-xs rounded-lg border ${
                        form.valid_hours === h ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600'
                      }`}
                    >
                      {h}h
                    </button>
                  ))}
                </div>
              </Field>
            )}
            <Field label="Email hosťa (voliteľné)">
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="input"
                placeholder="host@example.com"
              />
            </Field>
            <div className="flex gap-2 pt-2">
              <button onClick={createKey} disabled={saving} className="flex-1 bg-blue-600 text-white text-sm py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {saving ? 'Generujem...' : 'Vygenerovať kľúč'}
              </button>
              <button onClick={() => { setShowCreate(false); setError('') }} className="px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                Zrušiť
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal – nový kľúč (zobraz prihlasovacie údaje) */}
      {newKey && (
        <Modal title="Kľúč vygenerovaný" onClose={() => setNewKey(null)}>
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-xs text-green-700 mb-3">Heslo sa zobrazí len raz. Skopíruj ho teraz.</p>
              <div className="space-y-2">
                <div>
                  <span className="text-xs text-gray-500">Sieť:</span>
                  <span className="text-sm font-mono ml-2 font-bold">Oratko</span>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Meno:</span>
                  <span className="text-sm font-mono ml-2">{newKey.ldap_username}</span>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Heslo:</span>
                  <span className="text-sm font-mono ml-2 font-bold">{newKey.ldap_password}</span>
                </div>
              </div>
            </div>
            <button
              onClick={() => { showQR(newKey.id); setNewKey(null) }}
              className="w-full border border-gray-200 text-sm py-2.5 rounded-lg hover:bg-gray-50"
            >
              📷 Zobraziť QR kód
            </button>
            <button onClick={() => setNewKey(null)} className="w-full bg-blue-600 text-white text-sm py-2.5 rounded-lg hover:bg-blue-700">
              Hotovo
            </button>
          </div>
        </Modal>
      )}

      {/* Modal – QR */}
      {qr && (
        <Modal title="QR kód pre WiFi" onClose={() => setQr(null)}>
          <div className="text-center space-y-4">
            <img src={qr.qr_code} alt="WiFi QR kód" className="mx-auto rounded-lg max-w-48" />
            <p className="text-xs text-gray-500">
              Naskenuj QR kódom na iOS / Android pre automatické pripojenie na sieť Oratko.
            </p>
            <button onClick={() => setQr(null)} className="w-full bg-gray-100 text-sm py-2.5 rounded-lg hover:bg-gray-200">
              Zavrieť
            </button>
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
