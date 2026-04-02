'use client'

import { useState, useEffect, useCallback } from 'react'
import { api, type LDAPUser, type BulkCreateResponse, type GroupInfo } from '@/lib/api'
import { VlanInfoButton } from '@/components/VlanInfoButton'

type FormData = {
  first_name: string
  last_name: string
  email: string
  group: string
}

type UserDevice = {
  mac_address: string
  label: string
  first_seen: string
  last_seen: string
}

type UserDevicesData = {
  username: string
  max_devices: number
  devices: UserDevice[]
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
  const [showAddModal, setShowAddModal] = useState(false)
  const [addTab, setAddTab] = useState<'single' | 'bulk'>('single')
  const [form, setForm] = useState<FormData>(INITIAL_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [createdUser, setCreatedUser] = useState<CreatedUser | null>(null)
  const [showCreatedPassword, setShowCreatedPassword] = useState(false)
  const [resetPassResult, setResetPassResult] = useState<{ username: string; password: string; email: string; email_sent: boolean } | null>(null)
  const [showResetPassword, setShowResetPassword] = useState(false)
  const [resetPassSaving, setResetPassSaving] = useState<string | null>(null)
  const [selectedUser, setSelectedUser] = useState<LDAPUser | null>(null)
  const [showSearch, setShowSearch] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [devicesData, setDevicesData] = useState<UserDevicesData | null>(null)
  const [devicesLoading, setDevicesLoading] = useState(false)
  const [deviceLimitEdit, setDeviceLimitEdit] = useState<number | null>(null)
  const [deviceLimitSaving, setDeviceLimitSaving] = useState(false)
  const [resetConfirmUser, setResetConfirmUser] = useState<string | null>(null)
  const [editName, setEditName] = useState(false)
  const [nameForm, setNameForm] = useState({ first_name: '', last_name: '' })
  const [nameSaving, setNameSaving] = useState(false)
  const [bulkPhase, setBulkPhase] = useState<'input' | 'results'>('input')
  const [bulkEmails, setBulkEmails] = useState('')
  const [bulkGroup, setBulkGroup] = useState('')
  const [bulkResult, setBulkResult] = useState<BulkCreateResponse | null>(null)
  const [bulkSaving, setBulkSaving] = useState(false)

  useEffect(() => {
    api.get<GroupInfo[]>('/users/groups/').then((gs) => {
      setGroups(gs)
      setForm((f) => ({ ...f, group: f.group || gs[0]?.name || '' }))
      setBulkGroup((b) => b || gs[0]?.name || '')
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
      setShowAddModal(false)
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
    setSelectedUser(null)
    load()
  }

  async function deleteUser(username: string) {
    setDeleteConfirm(false)
    setSelectedUser(null)
    await api.delete(`/users/${username}/`)
    load()
  }

  function parsedEmails() {
    return bulkEmails
      .split(/[\n,;]+/)
      .map((e) => e.trim().toLowerCase())
      .filter((e) => e.includes('@'))
  }

  async function submitBulk() {
    const emails = parsedEmails()
    if (emails.length === 0) return
    setBulkSaving(true)
    try {
      const result = await api.post<BulkCreateResponse>('/users/bulk/', { emails, group: bulkGroup })
      setBulkResult(result)
      setBulkPhase('results')
      if (result.created > 0) load()
    } finally {
      setBulkSaving(false)
    }
  }

  function closeBulk() {
    setShowAddModal(false)
    setBulkPhase('input')
    setBulkEmails('')
    setBulkGroup(groups[0]?.name || '')
    setBulkResult(null)
  }

  async function loadDevices(username: string) {
    setDevicesLoading(true)
    try {
      const data = await api.get<UserDevicesData>(`/sessions/devices/${username}/`)
      setDevicesData(data)
      setDeviceLimitEdit(data.max_devices)
    } finally {
      setDevicesLoading(false)
    }
  }

  async function saveDeviceLimit(username: string) {
    if (deviceLimitEdit === null) return
    setDeviceLimitSaving(true)
    try {
      const result = await api.patch<{ max_devices: number }>(`/sessions/devices/${username}/`, { max_devices: deviceLimitEdit })
      setDevicesData((d) => d ? { ...d, max_devices: result.max_devices } : d)
    } finally {
      setDeviceLimitSaving(false)
    }
  }

  async function removeDevice(username: string, mac: string) {
    await api.delete(`/sessions/devices/${username}/${encodeURIComponent(mac)}/`)
    setDevicesData((d) => d ? { ...d, devices: d.devices.filter((dev) => dev.mac_address !== mac) } : d)
  }

  async function resetPassword(username: string) {
    setResetPassSaving(username)
    try {
      const result = await api.post<{ password: string; email_sent: boolean; email: string }>(
        `/users/${username}/password/`, {}
      )
      setResetPassResult({ username, ...result })
      setSelectedUser(null)
      setShowResetPassword(true)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Chyba pri resetovaní hesla')
    } finally {
      setResetPassSaving(null)
    }
  }

  async function saveName(username: string) {
    setNameSaving(true)
    try {
      const updated = await api.patch<LDAPUser>(`/users/${username}/`, nameForm)
      setSelectedUser(updated)
      setEditName(false)
      load()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Chyba pri ukladaní mena')
    } finally {
      setNameSaving(false)
    }
  }

  return (
    <div className="space-y-4 max-w-5xl">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-gray-900">Používatelia ({groups.reduce((s, g) => s + g.member_count, 0)})</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowSearch(!showSearch)}
            title="Vyhľadávanie a filtre"
            className={`relative btn-icon border transition-colors ${
              showSearch || search || groupFilter
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 text-gray-500 hover:bg-gray-50'
            }`}
          >
            <span>🔍</span>
            {(search || groupFilter) && (
              <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-blue-600" />
            )}
          </button>
          <button
            onClick={() => { setShowAddModal(true); setAddTab('single') }}
            className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            + Pridať
          </button>
        </div>
      </div>

      {/* Filtre – schovateľné */}
      {showSearch && (
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="search"
            placeholder="Hľadať meno, login, email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input flex-1"
            autoFocus
          />
          <select
            value={groupFilter}
            onChange={(e) => setGroupFilter(e.target.value)}
            className="input sm:w-48"
          >
            <option value="">Všetky skupiny</option>
            {groups.map((g) => (
              <option key={g.name} value={g.name}>{g.label}</option>
            ))}
          </select>
        </div>
      )}

      {/* Zoznam */}
      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="divide-y divide-gray-50">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="px-4 py-3 flex items-center gap-3">
                <div className="skeleton w-9 h-9 rounded-full flex-shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="skeleton h-3.5 w-32" />
                  <div className="skeleton h-3 w-48" />
                </div>
              </div>
            ))}
          </div>
        ) : users.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">Žiadni používatelia</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {users.map((user) => (
              <button
                key={user.username}
                onClick={() => { setSelectedUser(user); setDevicesData(null); setEditName(false); setNameForm({ first_name: user.first_name || '', last_name: user.last_name || '' }); loadDevices(user.username) }}
                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors text-left"
              >
                <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0 ${
                  user.disabled ? 'bg-gray-100 text-gray-400' : 'bg-blue-100 text-blue-700'
                }`}>
                  {(user.first_name?.[0] || user.username[0]).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm text-gray-900">
                      {user.full_name || user.username}
                    </span>
                    {user.disabled && (
                      <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">zablokovaný</span>
                    )}
                  </div>
                  <div className="text-xs text-gray-400 truncate">
                    {user.username}
                    {groups.find((g) => g.name === user.group) && ` · ${groups.find((g) => g.name === user.group)!.label}`}
                  </div>
                </div>
                <span className="text-gray-300 flex-shrink-0">›</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Modal – pridať používateľov (jeden / hromadný) */}
      {showAddModal && (
        <Modal
          title={bulkPhase === 'results' ? 'Výsledky importu' : 'Pridať používateľov'}
          onClose={() => { setShowAddModal(false); setError(''); setBulkPhase('input'); setBulkEmails(''); setBulkResult(null) }}
        >
          <div className="space-y-4">
            {/* Tab cards – skryť keď zobrazujeme výsledky */}
            {bulkPhase !== 'results' && (
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => { setAddTab('single'); setError('') }}
                  className={`p-3 rounded-xl border text-left transition-colors ${
                    addTab === 'single' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="text-sm font-medium text-gray-900">Jeden používateľ</div>
                  <div className="text-xs text-gray-400 mt-0.5">meno + email</div>
                </button>
                <button
                  onClick={() => { setAddTab('bulk'); setError('') }}
                  className={`p-3 rounded-xl border text-left transition-colors ${
                    addTab === 'bulk' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="text-sm font-medium text-gray-900">Hromadný import</div>
                  <div className="text-xs text-gray-400 mt-0.5">zoznam emailov</div>
                </button>
              </div>
            )}

            {/* Jeden používateľ */}
            {addTab === 'single' && bulkPhase !== 'results' && (
              <div className="space-y-3">
                {error && <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</div>}
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Meno *">
                    <input
                      value={form.first_name}
                      onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                      className="input"
                      placeholder="Ján"
                      required
                    />
                  </Field>
                  <Field label="Priezvisko *">
                    <input
                      value={form.last_name}
                      onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                      className="input"
                      placeholder="Novák"
                      required
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
                <Field label={<>Skupina / VLAN <VlanInfoButton /></>}>
                  <select value={form.group} onChange={(e) => setForm({ ...form, group: e.target.value })} className="input">
                    {groups.map((g) => <option key={g.name} value={g.name}>{g.label} – VLAN {g.vlan}</option>)}
                  </select>
                </Field>
                {!form.email && form.first_name && form.last_name && (
                  <p className="text-xs text-gray-400">
                    Login bude: <span className="font-mono text-gray-600">{slugify(form.first_name, form.last_name)}</span>
                  </p>
                )}
                <button
                  onClick={createUser}
                  disabled={saving || !form.first_name || !form.last_name}
                  className="w-full bg-blue-600 text-white text-sm py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Vytváram...' : 'Vytvoriť'}
                </button>
              </div>
            )}

            {/* Hromadný import */}
            {addTab === 'bulk' && bulkPhase === 'input' && (
              <div className="space-y-3">
                <Field label="Emailové adresy (každá na nový riadok alebo oddelené čiarkou)">
                  <textarea
                    value={bulkEmails}
                    onChange={(e) => setBulkEmails(e.target.value)}
                    className="input min-h-32 resize-y font-mono text-xs"
                    placeholder={'jan@example.sk\nanna@example.sk\npeter@example.sk'}
                  />
                  {parsedEmails().length > 0 && (
                    <p className="text-xs text-gray-400 mt-1">{parsedEmails().length} emailov</p>
                  )}
                </Field>
                <Field label={<>Skupina (pre všetkých) <VlanInfoButton /></>}>
                  <select value={bulkGroup} onChange={(e) => setBulkGroup(e.target.value)} className="input">
                    {groups.map((g) => (
                      <option key={g.name} value={g.name}>{g.label} – VLAN {g.vlan}</option>
                    ))}
                  </select>
                </Field>
                <div className="bg-gray-50 rounded-lg px-3 py-2 text-xs text-gray-500 space-y-1">
                  <div>Login = emailová adresa</div>
                  <div>Meno = názov skupiny · Priezvisko = poradové číslo</div>
                  <div>Heslo (8 znakov) sa automaticky odošle na každý email</div>
                </div>
                <button
                  onClick={submitBulk}
                  disabled={bulkSaving || parsedEmails().length === 0}
                  className="w-full bg-blue-600 text-white text-sm py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {bulkSaving ? 'Vytváram...' : `Vytvoriť ${parsedEmails().length} používateľov`}
                </button>
              </div>
            )}

            {/* Výsledky hromadného importu */}
            {bulkPhase === 'results' && bulkResult && (
              <div className="space-y-3">
                <div className="flex gap-3 text-sm">
                  <span className="text-green-600 font-medium">✓ Vytvorených: {bulkResult.created}</span>
                  {bulkResult.failed > 0 && (
                    <span className="text-red-500 font-medium">✗ Zlyhalo: {bulkResult.failed}</span>
                  )}
                </div>
                {bulkResult.created > 0 && (
                  <p className="text-xs text-blue-600 bg-blue-50 px-3 py-2 rounded-lg">
                    Heslo bolo odoslané na každý email.
                  </p>
                )}
                <div className="max-h-64 overflow-y-auto space-y-1">
                  {bulkResult.results.map((r) => (
                    <div key={r.index} className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${r.success ? 'bg-green-50' : 'bg-red-50'}`}>
                      {r.success ? (
                        <>
                          <span className="text-green-600 flex-shrink-0">✓</span>
                          <span className="font-mono text-gray-700">{r.email}</span>
                        </>
                      ) : (
                        <>
                          <span className="text-red-500 flex-shrink-0">✗</span>
                          <span className="text-gray-600 font-mono">{r.email}</span>
                          <span className="text-red-500 truncate">{r.error}</span>
                        </>
                      )}
                    </div>
                  ))}
                </div>
                <button onClick={closeBulk} className="w-full bg-blue-600 text-white text-sm py-2.5 rounded-lg hover:bg-blue-700">
                  Hotovo
                </button>
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Modal – výsledok vytvorenia */}
      {createdUser && (
        <Modal title="Používateľ vytvorený" onClose={() => { setCreatedUser(null); setShowCreatedPassword(false) }}>
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-sm text-green-700">
              Účet bol úspešne vytvorený.
              {createdUser.email && ' Prihlasovacie údaje boli odoslané emailom.'}
            </div>
            <div className="bg-gray-50 rounded-xl border border-gray-200 divide-y divide-gray-200 overflow-hidden">
              <div className="flex items-center px-4 py-3 gap-3 min-w-0">
                <span className="text-xs text-gray-400 w-16 flex-shrink-0">Login</span>
                <span className="font-mono text-sm text-gray-900 flex-1 break-all">{createdUser.username}</span>
                <button
                  onClick={() => navigator.clipboard.writeText(createdUser.username)}
                  className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 flex-shrink-0"
                >
                  Kop.
                </button>
              </div>
              <div className="flex items-center px-4 py-3 gap-3 min-w-0">
                <span className="text-xs text-gray-400 w-16 flex-shrink-0">Heslo</span>
                <span className="font-mono text-sm font-bold text-gray-900 flex-1 tracking-wider">
                  {showCreatedPassword ? createdUser.password : '••••••••'}
                </span>
                <button
                  onClick={() => setShowCreatedPassword(!showCreatedPassword)}
                  className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 flex-shrink-0"
                >
                  {showCreatedPassword ? 'Skryť' : 'Zobraziť'}
                </button>
                <button
                  onClick={() => navigator.clipboard.writeText(createdUser.password)}
                  className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 flex-shrink-0"
                >
                  Kop.
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

      {/* Modal – detail používateľa */}
      {selectedUser && (
        <Modal
          title="Detail používateľa"
          onClose={() => { setSelectedUser(null); setDeleteConfirm(false); setResetConfirmUser(null); setDevicesData(null); setEditName(false) }}
        >
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold flex-shrink-0 ${
                selectedUser.disabled ? 'bg-gray-100 text-gray-400' : 'bg-blue-100 text-blue-700'
              }`}>
                {(selectedUser.first_name?.[0] || selectedUser.username[0]).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                {editName ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        value={nameForm.first_name}
                        onChange={(e) => setNameForm({ ...nameForm, first_name: e.target.value })}
                        className="input text-sm"
                        placeholder="Meno"
                        autoFocus
                      />
                      <input
                        value={nameForm.last_name}
                        onChange={(e) => setNameForm({ ...nameForm, last_name: e.target.value })}
                        className="input text-sm"
                        placeholder="Priezvisko"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => saveName(selectedUser.username)}
                        disabled={nameSaving}
                        className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                      >
                        {nameSaving ? 'Ukladám...' : 'Uložiť'}
                      </button>
                      <button
                        onClick={() => setEditName(false)}
                        className="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
                      >
                        Zrušiť
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-2">
                    <div className="min-w-0">
                      <div className="font-semibold text-gray-900 text-base">{selectedUser.full_name || selectedUser.username}</div>
                      <div className="text-sm text-gray-400 truncate">{selectedUser.username}</div>
                    </div>
                    <button
                      onClick={() => setEditName(true)}
                      className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 flex-shrink-0 mt-0.5"
                      title="Upraviť meno"
                    >
                      Upraviť
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-gray-50 rounded-xl border border-gray-200 divide-y divide-gray-200 overflow-hidden text-sm">
              {selectedUser.email && (
                <div className="flex items-center gap-3 px-4 py-3">
                  <span className="text-xs text-gray-400 w-16 flex-shrink-0">Email</span>
                  <span className="text-gray-700 flex-1 break-all">{selectedUser.email}</span>
                </div>
              )}
              <div className="flex items-center gap-3 px-4 py-3">
                <span className="text-xs text-gray-400 w-16 flex-shrink-0">Skupina</span>
                <span className="text-gray-700">
                  {groups.find((g) => g.name === selectedUser.group)?.label || selectedUser.group}
                  {groups.find((g) => g.name === selectedUser.group)?.vlan
                    ? ` · VLAN ${groups.find((g) => g.name === selectedUser.group)!.vlan}`
                    : ''}
                </span>
              </div>
              <div className="flex items-center gap-3 px-4 py-3">
                <span className="text-xs text-gray-400 w-16 flex-shrink-0">Stav</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  selectedUser.disabled ? 'bg-gray-100 text-gray-500' : 'bg-green-100 text-green-700'
                }`}>
                  {selectedUser.disabled ? 'Zablokovaný' : 'Aktívny'}
                </span>
              </div>
            </div>

            {/* Zariadenia + limit */}
            <div className="bg-gray-50 rounded-xl border border-gray-200 overflow-hidden">
              {/* Riadok: limit zariadení */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200">
                <span className="text-xs text-gray-400 w-16 flex-shrink-0">Limit</span>
                {devicesData ? (
                  <div className="flex items-center gap-2 flex-1">
                    <button
                      onClick={() => setDeviceLimitEdit(Math.max(1, (deviceLimitEdit ?? devicesData.max_devices) - 1))}
                      className="w-7 h-7 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-100 text-sm font-bold flex items-center justify-center"
                    >−</button>
                    <span className="text-sm font-semibold text-gray-900 w-6 text-center">
                      {deviceLimitEdit ?? devicesData.max_devices}
                    </span>
                    <button
                      onClick={() => setDeviceLimitEdit((deviceLimitEdit ?? devicesData.max_devices) + 1)}
                      className="w-7 h-7 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-100 text-sm font-bold flex items-center justify-center"
                    >+</button>
                    {deviceLimitEdit !== null && deviceLimitEdit !== devicesData.max_devices && (
                      <button
                        onClick={() => saveDeviceLimit(selectedUser.username)}
                        disabled={deviceLimitSaving}
                        className="ml-1 text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                      >
                        {deviceLimitSaving ? 'Ukladám...' : 'Uložiť'}
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="skeleton h-7 w-24 rounded-lg" />
                )}
              </div>

              {/* Zoznam zariadení */}
              {devicesLoading ? (
                <div className="px-4 py-3 text-xs text-gray-400">Načítavam zariadenia...</div>
              ) : devicesData && devicesData.devices.length === 0 ? (
                <div className="px-4 py-3 text-xs text-gray-400">
                  Žiadne zariadenia. Registrujú sa automaticky pri prvom pripojení.
                </div>
              ) : devicesData ? (
                <div className="divide-y divide-gray-100">
                  {devicesData.devices.map((dev) => (
                    <div key={dev.mac_address} className="flex items-center gap-3 px-4 py-2.5">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-gray-800 font-medium truncate">
                          {dev.label || dev.mac_address}
                        </div>
                        <div className="text-xs text-gray-400 font-mono">
                          {dev.label ? dev.mac_address : null}
                          {dev.label ? ' · ' : ''}
                          naposledy {new Date(dev.last_seen).toLocaleDateString('sk-SK')}
                        </div>
                      </div>
                      <button
                        onClick={() => removeDevice(selectedUser.username, dev.mac_address)}
                        className="text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50 flex-shrink-0"
                      >
                        Odstrániť
                      </button>
                    </div>
                  ))}
                </div>
              ) : null}

              {/* Počítadlo */}
              {devicesData && (
                <div className={`px-4 py-2 text-xs ${
                  devicesData.devices.length >= devicesData.max_devices
                    ? 'bg-amber-50 text-amber-700 border-t border-amber-100'
                    : 'bg-green-50 text-green-700 border-t border-green-100'
                }`}>
                  {devicesData.devices.length} / {devicesData.max_devices} zariadení
                  {devicesData.devices.length >= devicesData.max_devices && ' · limit dosiahnutý'}
                </div>
              )}
            </div>

            <div className="space-y-2">
              {resetConfirmUser !== selectedUser.username ? (
                <button
                  onClick={() => setResetConfirmUser(selectedUser.username)}
                  disabled={resetPassSaving === selectedUser.username}
                  className="w-full flex items-center gap-2 px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-xl border border-gray-200 transition-colors disabled:opacity-50"
                >
                  <span>🔒</span>
                  <span>Resetovať heslo</span>
                </button>
              ) : (
                <div className="flex items-center gap-2 px-4 py-3 bg-amber-50 rounded-xl border border-amber-200">
                  <span className="text-sm text-amber-800 flex-1">Naozaj resetovať heslo?</span>
                  <button
                    onClick={() => { setResetConfirmUser(null); resetPassword(selectedUser.username) }}
                    disabled={resetPassSaving === selectedUser.username}
                    className="text-sm px-3 py-1.5 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50"
                  >
                    {resetPassSaving === selectedUser.username ? 'Generujem...' : 'Áno'}
                  </button>
                  <button
                    onClick={() => setResetConfirmUser(null)}
                    className="text-sm px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
                  >
                    Nie
                  </button>
                </div>
              )}
              <button
                onClick={() => toggleActive(selectedUser)}
                className={`w-full flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-xl border transition-colors ${
                  selectedUser.disabled
                    ? 'text-green-700 bg-green-50 hover:bg-green-100 border-green-200'
                    : 'text-amber-700 bg-amber-50 hover:bg-amber-100 border-amber-200'
                }`}
              >
                <span>{selectedUser.disabled ? '✅' : '🚫'}</span>
                <span>{selectedUser.disabled ? 'Odblokovať účet' : 'Zablokovať účet'}</span>
              </button>
              {!deleteConfirm ? (
                <button
                  onClick={() => setDeleteConfirm(true)}
                  className="w-full flex items-center gap-2 px-4 py-3 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-xl border border-red-200 transition-colors"
                >
                  <span>🗑</span>
                  <span>Odstrániť používateľa</span>
                </button>
              ) : (
                <div className="flex items-center gap-2 px-4 py-3 bg-red-50 rounded-xl border border-red-200">
                  <span className="text-sm text-red-700 flex-1">Naozaj odstrániť?</span>
                  <button
                    onClick={() => deleteUser(selectedUser.username)}
                    className="text-sm px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700"
                  >
                    Áno
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(false)}
                    className="text-sm px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
                  >
                    Nie
                  </button>
                </div>
              )}
            </div>
          </div>
        </Modal>
      )}

      {/* Modal – nové vygenerované heslo */}
      {showResetPassword && resetPassResult && (
        <Modal title="Nové heslo vygenerované" onClose={() => { setShowResetPassword(false); setResetPassResult(null); setShowCreatedPassword(false) }}>
          <div className="space-y-4">
            <div className={`border rounded-xl px-4 py-3 text-sm ${resetPassResult.email_sent ? 'bg-green-50 border-green-200 text-green-700' : 'bg-amber-50 border-amber-200 text-amber-700'}`}>
              {resetPassResult.email_sent
                ? `Nové heslo bolo odoslané na ${resetPassResult.email}.`
                : 'Používateľ nemá email – heslo si skopíruj manuálne.'}
            </div>
            <div className="bg-gray-50 rounded-xl border border-gray-200 divide-y divide-gray-200 overflow-hidden">
              <div className="flex items-center px-4 py-3 gap-3 min-w-0">
                <span className="text-xs text-gray-400 w-16 flex-shrink-0">Login</span>
                <span className="font-mono text-sm text-gray-900 flex-1 break-all">{resetPassResult.username}</span>
                <button
                  onClick={() => navigator.clipboard.writeText(resetPassResult.username)}
                  className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 flex-shrink-0"
                >
                  Kop.
                </button>
              </div>
              <div className="flex items-center px-4 py-3 gap-3 min-w-0">
                <span className="text-xs text-gray-400 w-16 flex-shrink-0">Heslo</span>
                <span className="font-mono text-sm font-bold text-gray-900 flex-1 tracking-wider">
                  {showCreatedPassword ? resetPassResult.password : '••••••••'}
                </span>
                <button
                  onClick={() => setShowCreatedPassword(!showCreatedPassword)}
                  className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 flex-shrink-0"
                >
                  {showCreatedPassword ? 'Skryť' : 'Zobraziť'}
                </button>
                <button
                  onClick={() => navigator.clipboard.writeText(resetPassResult.password)}
                  className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 flex-shrink-0"
                >
                  Kop.
                </button>
              </div>
            </div>
            <button
              onClick={() => { setShowResetPassword(false); setResetPassResult(null); setShowCreatedPassword(false) }}
              className="w-full bg-blue-600 text-white text-sm py-2.5 rounded-lg hover:bg-blue-700"
            >
              Hotovo
            </button>
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
