'use client'

import { useState, useEffect, useCallback } from 'react'
import { api, type TempKey, type GroupInfo } from '@/lib/api'
import { formatDate, formatRelative } from '@/lib/utils'
import { VlanInfoButton } from '@/components/VlanInfoButton'

export default function KeysPage() {
  const [keys, setKeys] = useState<TempKey[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newKey, setNewKey] = useState<TempKey | null>(null)
  const [qr, setQr] = useState<{ qr_code: string; username: string } | null>(null)
  const [groups, setGroups] = useState<GroupInfo[]>([])
  const [form, setForm] = useState({
    label: '',
    group: '',
    key_type: 'multi_use' as 'timed' | 'multi_use',
    expiry_mode: 'hours' as 'hours' | 'datetime',
    valid_hours: 24,
    duration_unit: 'h' as 'h' | 'min',
    duration_value: 24,
    expires_date: '',
    expires_time: (() => { const d = new Date(Date.now() + 3600000); return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}` })(),
    max_uses: 1,
    email: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [activeOnly, setActiveOnly] = useState(false)
  const [showNewKeyPassword, setShowNewKeyPassword] = useState(false)

  // Detail modal state
  const [selectedKey, setSelectedKey] = useState<TempKey | null>(null)
  const [selectedKeyLoading, setSelectedKeyLoading] = useState(false)
  const [showKeyPassword, setShowKeyPassword] = useState(false)
  const [resendEmail, setResendEmail] = useState('')
  const [resendSaving, setResendSaving] = useState(false)
  const [resendResult, setResendResult] = useState('')
  const [deleteConfirmDetail, setDeleteConfirmDetail] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    const params = activeOnly ? '?active=1' : ''
    api.get<TempKey[]>(`/keys/${params}`).then(setKeys).finally(() => setLoading(false))
  }, [activeOnly])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    api.get<GroupInfo[]>('/users/groups/').then((data) => {
      setGroups(data)
      if (data.length > 0) setForm((f) => ({ ...f, group: f.group || data[0].name }))
    })
  }, [])

  async function createKey() {
    setSaving(true)
    setError('')
    try {
      const body: Record<string, unknown> = {
        label: form.label,
        group: form.group,
        key_type: form.key_type,
        email: form.email,
      }
      if (form.key_type === 'timed') {
        if (form.expiry_mode === 'datetime') {
          if (!form.expires_date) { setError('Zadaj dátum expirácie.'); setSaving(false); return }
          const dt = new Date(`${form.expires_date}T${form.expires_time}:00`)
          if (isNaN(dt.getTime()) || dt <= new Date()) { setError('Dátum expirácie musí byť v budúcnosti.'); setSaving(false); return }
          body.expires_at = dt.toISOString()
        } else {
          body.valid_hours = form.duration_unit === 'min'
            ? form.duration_value / 60
            : form.duration_value
        }
      }
      if (form.key_type === 'multi_use') {
        body.max_uses = form.max_uses
      }
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

  async function openKeyDetail(id: string) {
    setSelectedKeyLoading(true)
    setShowKeyPassword(false)
    setResendEmail('')
    setResendResult('')
    setDeleteConfirmDetail(false)
    try {
      const key = await api.get<TempKey>(`/keys/${id}/`)
      setSelectedKey(key)
    } finally {
      setSelectedKeyLoading(false)
    }
  }

  function closeKeyDetail() {
    setSelectedKey(null)
    setShowKeyPassword(false)
    setResendEmail('')
    setResendResult('')
    setDeleteConfirmDetail(false)
  }

  async function deleteSelectedKey() {
    if (!selectedKey) return
    await api.delete(`/keys/${selectedKey.id}/`)
    closeKeyDetail()
    load()
  }

  async function resendKeyEmail() {
    if (!selectedKey || !resendEmail) return
    setResendSaving(true)
    setResendResult('')
    try {
      await api.post(`/keys/${selectedKey.id}/send-email/`, { email: resendEmail })
      setResendResult(`Email odoslaný na ${resendEmail}`)
      setResendEmail('')
    } catch (e) {
      setResendResult(e instanceof Error ? e.message : 'Chyba')
    } finally {
      setResendSaving(false)
    }
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
              <button
                key={key.id}
                onClick={() => openKeyDetail(key.id)}
                className="w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                    key.is_active ? 'bg-green-400' : key.used ? 'bg-gray-300' : 'bg-red-400'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm text-gray-900">{key.ldap_username}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        key.key_type === 'multi_use' || key.key_type === 'one_time'
                          ? 'bg-orange-100 text-orange-700'
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {key.key_type === 'one_time'
                          ? `${key.used ? 1 : 0}/1×`
                          : key.key_type === 'multi_use'
                            ? `${key.use_count}/${key.max_uses}×`
                            : key.valid_hours
                              ? `${key.valid_hours}h`
                              : `do ${formatDate(key.expires_at)}`}
                      </span>
                      {key.used && <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">vyčerpaný</span>}
                      {key.is_expired && !key.used && <span className="text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded">expirovaný</span>}
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {key.label && `${key.label} · `}
                      Vytvorený {formatRelative(key.created_at)}
                      {key.expires_at && ` · Expiruje ${formatDate(key.expires_at)}`}
                      {key.email_sent_to && ` · Email: ${key.email_sent_to}`}
                    </div>
                  </div>
                  <span className="text-gray-300 text-sm flex-shrink-0">›</span>
                </div>
              </button>
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
            <Field label={<>Skupina / VLAN <VlanInfoButton /></>}>
              <select
                value={form.group}
                onChange={(e) => setForm({ ...form, group: e.target.value })}
                className="input"
              >
                {groups.map((g) => (
                  <option key={g.name} value={g.name}>
                    {g.label} (VLAN {g.vlan})
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Typ kľúča">
              <div className="grid grid-cols-2 gap-2">
                <label className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer ${
                  form.key_type === 'multi_use' ? 'border-orange-500 bg-orange-50' : 'border-gray-200'
                }`}>
                  <input
                    type="radio"
                    value="multi_use"
                    checked={form.key_type === 'multi_use'}
                    onChange={() => setForm({ ...form, key_type: 'multi_use' })}
                    className="sr-only"
                  />
                  <div>
                    <div className="text-sm font-medium">N-násobný</div>
                    <div className="text-xs text-gray-400">1× = jednorazový</div>
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
                    <div className="text-xs text-gray-400">platný N hodín</div>
                  </div>
                </label>
              </div>
            </Field>
            {form.key_type === 'timed' && (
              <>
                <Field label="Spôsob expirácie">
                  <div className="grid grid-cols-2 gap-2">
                    <label className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer ${
                      form.expiry_mode === 'hours' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}>
                      <input
                        type="radio"
                        checked={form.expiry_mode === 'hours'}
                        onChange={() => setForm({ ...form, expiry_mode: 'hours' })}
                        className="sr-only"
                      />
                      <div>
                        <div className="text-xs font-medium">Za N hodín</div>
                        <div className="text-xs text-gray-400">relatívne</div>
                      </div>
                    </label>
                    <label className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer ${
                      form.expiry_mode === 'datetime' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}>
                      <input
                        type="radio"
                        checked={form.expiry_mode === 'datetime'}
                        onChange={() => setForm({ ...form, expiry_mode: 'datetime' })}
                        className="sr-only"
                      />
                      <div>
                        <div className="text-xs font-medium">Dátum a čas</div>
                        <div className="text-xs text-gray-400">absolútne</div>
                      </div>
                    </label>
                  </div>
                </Field>
                {form.expiry_mode === 'hours' ? (
                  <Field label="Platnosť">
                    <div className="space-y-3 pt-1">
                      {/* Hodnota + toggle prepínač */}
                      <div className="flex items-center justify-between">
                        <span className="text-3xl font-bold text-gray-900 tabular-nums">
                          {form.duration_value}
                          <span className="text-base font-normal text-gray-400 ml-1.5">
                            {form.duration_unit === 'min' ? 'minút' : 'hodín'}
                          </span>
                        </span>
                        <div className="flex items-center gap-2 select-none">
                          <span className={`text-sm ${form.duration_unit === 'min' ? 'text-blue-600 font-semibold' : 'text-gray-400'}`}>min</span>
                          <button
                            type="button"
                            onClick={() => {
                              const newUnit = form.duration_unit === 'min' ? 'h' : 'min'
                              const newValue = newUnit === 'min'
                                ? Math.min(240, Math.round(form.duration_value * 60 / 5) * 5)
                                : Math.max(1, Math.round(form.duration_value / 60))
                              setForm({ ...form, duration_unit: newUnit, duration_value: newValue })
                            }}
                            className="relative w-12 h-6 rounded-full bg-gray-200 focus:outline-none overflow-hidden"
                          >
                            <span className={`absolute top-0.5 left-0 w-5 h-5 rounded-full shadow transition-transform ${
                              form.duration_unit === 'min' ? 'translate-x-0.5 bg-blue-500' : 'translate-x-6 bg-blue-500'
                            }`} />
                          </button>
                          <span className={`text-sm ${form.duration_unit === 'h' ? 'text-blue-600 font-semibold' : 'text-gray-400'}`}>hod</span>
                        </div>
                      </div>
                      {/* Slider */}
                      <input
                        type="range"
                        min={form.duration_unit === 'min' ? 5 : 1}
                        max={form.duration_unit === 'min' ? 240 : 48}
                        step={form.duration_unit === 'min' ? 5 : 1}
                        value={form.duration_value}
                        onChange={(e) => setForm({ ...form, duration_value: parseInt(e.target.value) })}
                        className="w-full accent-blue-500 cursor-pointer"
                      />
                      <div className="flex justify-between text-xs text-gray-400">
                        <span>{form.duration_unit === 'min' ? '5 min' : '1 hod'}</span>
                        <span>{form.duration_unit === 'min' ? '4 hod' : '48 hod'}</span>
                      </div>
                    </div>
                    {form.duration_unit === 'h' && form.duration_value > 24 && (
                      <p className="text-xs text-amber-600 mt-1">Pre dlhšie ako 24h použi možnosť „Dátum a čas".</p>
                    )}
                  </Field>
                ) : (
                  <Field label="Platný do">
                    <div className="flex gap-2">
                      <input
                        type="date"
                        value={form.expires_date}
                        onChange={(e) => { setError(''); setForm({ ...form, expires_date: e.target.value }) }}
                        className="input flex-1"
                      />
                      <input
                        type="time"
                        value={form.expires_time}
                        onChange={(e) => { setError(''); setForm({ ...form, expires_time: e.target.value }) }}
                        className="input w-28"
                      />
                    </div>
                    {(() => {
                      if (!form.expires_date) return null
                      const dt = new Date(`${form.expires_date}T${form.expires_time}:00`)
                      const diffMs = dt.getTime() - Date.now()
                      if (isNaN(dt.getTime())) return (
                        <p className="text-xs text-red-500 mt-1">Neplatný formát času.</p>
                      )
                      if (diffMs <= 0) return (
                        <p className="text-xs text-red-500 mt-1">Čas je v minulosti.</p>
                      )
                      const diffMin = Math.round(diffMs / 60000)
                      const label = diffMin < 60
                        ? `za ${diffMin} min`
                        : diffMin < 1440
                          ? `za ${Math.round(diffMin / 60)} hod`
                          : `za ${Math.round(diffMin / 1440)} dní`
                      return (
                        <p className="text-xs text-gray-400 mt-1">Expiruje {label} · {formatDate(dt.toISOString())}</p>
                      )
                    })()}
                  </Field>
                )}
              </>
            )}
            {form.key_type === 'multi_use' && (
              <Field label="Počet prihlásení">
                <div className="flex gap-2">
                  {[1, 2, 5, 10, 20, 50].map((n) => (
                    <button
                      key={n}
                      onClick={() => setForm({ ...form, max_uses: n })}
                      className={`flex-1 py-1.5 text-xs rounded-lg border ${
                        form.max_uses === n ? 'border-orange-500 bg-orange-50 text-orange-700' : 'border-gray-200 text-gray-600'
                      }`}
                    >
                      {n}×
                    </button>
                  ))}
                  <input
                    type="number"
                    min={2}
                    max={1000}
                    value={form.max_uses}
                    onChange={(e) => setForm({ ...form, max_uses: parseInt(e.target.value) || 2 })}
                    className="w-16 border border-gray-200 rounded-lg px-2 text-xs text-center focus:outline-none focus:ring-2 focus:ring-orange-400"
                  />
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
        <Modal title="Kľúč vygenerovaný" onClose={() => { setNewKey(null); setShowNewKeyPassword(false) }}>
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-xs text-green-700 mb-3">Heslo sa zobrazí len raz. Skopíruj ho teraz.</p>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-10 flex-shrink-0">Sieť:</span>
                  <span className="text-sm font-mono font-bold">Oratko</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-10 flex-shrink-0">Meno:</span>
                  <span className="text-sm font-mono flex-1">{newKey.ldap_username}</span>
                  <button onClick={() => navigator.clipboard.writeText(newKey.ldap_username)} className="text-xs text-gray-400 hover:text-gray-600 px-1.5 py-0.5 rounded hover:bg-green-100">Kop.</button>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-10 flex-shrink-0">Heslo:</span>
                  <span className="text-sm font-mono font-bold flex-1 tracking-wider">
                    {showNewKeyPassword ? newKey.ldap_password : '••••••••'}
                  </span>
                  <button onClick={() => setShowNewKeyPassword(!showNewKeyPassword)} className="text-xs text-gray-400 hover:text-gray-600 px-1.5 py-0.5 rounded hover:bg-green-100">
                    {showNewKeyPassword ? 'Skryť' : 'Zobraziť'}
                  </button>
                  <button onClick={() => navigator.clipboard.writeText(newKey.ldap_password ?? '')} className="text-xs text-gray-400 hover:text-gray-600 px-1.5 py-0.5 rounded hover:bg-green-100">Kop.</button>
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

      {/* Modal – detail kľúča */}
      {(selectedKey || selectedKeyLoading) && (
        <Modal title="Detail kľúča" onClose={closeKeyDetail}>
          {selectedKeyLoading ? (
            <div className="py-8 text-center text-gray-400 text-sm">Načítavam...</div>
          ) : selectedKey ? (
            <div className="space-y-4">
              {/* Header */}
              <div className="flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                  selectedKey.is_active ? 'bg-green-400' : selectedKey.used ? 'bg-gray-300' : 'bg-red-400'
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-gray-900">{selectedKey.ldap_username}</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {selectedKey.label && `${selectedKey.label} · `}
                    Vytvorený {formatRelative(selectedKey.created_at)}
                  </div>
                </div>
                <span className={`text-xs px-1.5 py-0.5 rounded flex-shrink-0 ${
                  selectedKey.key_type === 'multi_use' || selectedKey.key_type === 'one_time'
                    ? 'bg-orange-100 text-orange-700'
                    : 'bg-blue-100 text-blue-700'
                }`}>
                  {selectedKey.key_type === 'one_time'
                    ? `${selectedKey.used ? 1 : 0}/1×`
                    : selectedKey.key_type === 'multi_use'
                      ? `${selectedKey.use_count}/${selectedKey.max_uses}×`
                      : selectedKey.valid_hours
                        ? `${selectedKey.valid_hours}h`
                        : `do ${formatDate(selectedKey.expires_at)}`}
                </span>
              </div>

              {/* Credentials */}
              <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-12 flex-shrink-0">Sieť:</span>
                  <span className="text-sm font-mono">Oratko</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-12 flex-shrink-0">Meno:</span>
                  <span className="text-sm font-mono flex-1 truncate">{selectedKey.ldap_username}</span>
                  <button
                    onClick={() => navigator.clipboard.writeText(selectedKey.ldap_username)}
                    className="text-xs text-gray-400 hover:text-gray-600 px-1.5 py-0.5 rounded hover:bg-gray-200 flex-shrink-0"
                  >Kop.</button>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-12 flex-shrink-0">Heslo:</span>
                  <span className="text-sm font-mono font-bold flex-1 tracking-wider">
                    {showKeyPassword ? selectedKey.ldap_password : '••••••••'}
                  </span>
                  <button
                    onClick={() => setShowKeyPassword(!showKeyPassword)}
                    className="text-xs text-gray-400 hover:text-gray-600 px-1.5 py-0.5 rounded hover:bg-gray-200 flex-shrink-0"
                  >{showKeyPassword ? 'Skryť' : 'Zobraziť'}</button>
                  <button
                    onClick={() => navigator.clipboard.writeText(selectedKey.ldap_password ?? '')}
                    className="text-xs text-gray-400 hover:text-gray-600 px-1.5 py-0.5 rounded hover:bg-gray-200 flex-shrink-0"
                  >Kop.</button>
                </div>
              </div>

              {/* QR */}
              <button
                onClick={() => { showQR(selectedKey.id); closeKeyDetail() }}
                className="w-full border border-gray-200 text-sm py-2.5 rounded-lg hover:bg-gray-50 flex items-center justify-center gap-2"
              >
                <span>📷</span> Zobraziť QR kód
              </button>

              {/* Resend email */}
              <div className="space-y-2">
                <label className="block text-xs font-medium text-gray-600">Preposlať prihlasovacie údaje e-mailom</label>
                <div className="flex gap-2">
                  <input
                    type="email"
                    value={resendEmail}
                    onChange={(e) => { setResendEmail(e.target.value); setResendResult('') }}
                    placeholder="host@example.com"
                    className="input flex-1"
                  />
                  <button
                    onClick={resendKeyEmail}
                    disabled={resendSaving || !resendEmail}
                    className="px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 flex-shrink-0"
                    style={{ minHeight: 44 }}
                  >
                    {resendSaving ? '...' : 'Poslať'}
                  </button>
                </div>
                {resendResult && (
                  <p className={`text-xs ${resendResult.startsWith('Email') ? 'text-green-600' : 'text-red-600'}`}>
                    {resendResult}
                  </p>
                )}
              </div>

              {/* Delete */}
              <div className="pt-2 border-t border-gray-100">
                {deleteConfirmDetail ? (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 flex-1">Naozaj zmazať kľúč?</span>
                    <button onClick={deleteSelectedKey} className="text-xs px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700">Zmazať</button>
                    <button onClick={() => setDeleteConfirmDetail(false)} className="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200">Zrušiť</button>
                  </div>
                ) : (
                  <button
                    onClick={() => setDeleteConfirmDetail(true)}
                    className="w-full text-sm py-2.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 transition-colors"
                  >
                    Zmazať kľúč
                  </button>
                )}
              </div>
            </div>
          ) : null}
        </Modal>
      )}

      {/* Modal – QR */}
      {qr && (
        <Modal title="QR kód pre WiFi" onClose={() => setQr(null)}>
          <div className="text-center space-y-4">
            <img
              src={qr.qr_code.startsWith('data:image/') ? qr.qr_code : ''}
              alt="WiFi QR kód"
              className="mx-auto rounded-lg max-w-48"
            />
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" style={{ padding: '16px 16px calc(16px + env(safe-area-inset-bottom))' }}>
      <div className="bg-white rounded-2xl w-full max-w-md shadow-xl flex flex-col" style={{ maxHeight: 'min(90vh, calc(100dvh - 80px))' }}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 flex-shrink-0">
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <button onClick={onClose} className="btn-icon text-gray-400 hover:text-gray-600 hover:bg-gray-100">✕</button>
        </div>
        <div className="p-5 overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: React.ReactNode; children: React.ReactNode }) {
  return (
    <div>
      <label className="flex items-center gap-1.5 text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  )
}
