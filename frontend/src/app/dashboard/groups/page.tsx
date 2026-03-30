'use client'

import { useState, useEffect, useCallback } from 'react'
import { api, type GroupInfo, type LDAPUser } from '@/lib/api'

const VLAN_COLORS: Record<number, string> = {
  10: 'bg-blue-100 text-blue-700',
  20: 'bg-green-100 text-green-700',
  30: 'bg-yellow-100 text-yellow-700',
  40: 'bg-gray-100 text-gray-600',
}

export default function GroupsPage() {
  const [groups, setGroups] = useState<GroupInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [moving, setMoving] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    api.get<GroupInfo[]>('/users/groups/?detail=1')
      .then(setGroups)
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  async function moveUser(username: string, newGroup: string) {
    setMoving(username)
    try {
      await api.patch(`/users/${username}/`, { group: newGroup })
      setGroups((prev) => {
        const user = prev.flatMap((g) => g.members).find((m) => m.username === username)
        return prev.map((g) => {
          const hasUser = g.members.some((m) => m.username === username)
          if (g.name === newGroup && user) {
            return {
              ...g,
              members: hasUser ? g.members : [...g.members, { ...user, group: newGroup }],
              member_count: hasUser ? g.member_count : g.member_count + 1,
            }
          }
          if (hasUser && g.name !== newGroup) {
            return {
              ...g,
              members: g.members.filter((m) => m.username !== username),
              member_count: g.member_count - 1,
            }
          }
          return g
        })
      })
    } catch {
      load()
    } finally {
      setMoving(null)
    }
  }

  async function deleteGroup(name: string) {
    setDeleting(name)
    try {
      await api.delete(`/users/groups/${name}/`)
      setGroups((prev) => prev.filter((g) => g.name !== name))
      if (expanded === name) setExpanded(null)
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Chyba pri mazaní skupiny')
    } finally {
      setDeleting(null)
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-gray-400 text-sm">Načítavam skupiny...</div>
  }

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Skupiny</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">{groups.reduce((s, g) => s + g.member_count, 0)} používateľov celkom</span>
          <button
            onClick={() => setShowCreate(true)}
            className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg font-medium transition-colors"
          >
            + Pridať skupinu
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {groups.map((group) => (
          <div key={group.name} className="bg-white rounded-xl border border-gray-100 overflow-hidden">
            <div
              className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors"
              onClick={() => setExpanded(expanded === group.name ? null : group.name)}
            >
              <div className="flex items-center gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm text-gray-900">{group.label}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${VLAN_COLORS[group.vlan] ?? 'bg-gray-100 text-gray-600'}`}>
                      VLAN {group.vlan}
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">{group.member_count} členov</div>
                </div>
              </div>
              <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                {group.member_count === 0 && (
                  <button
                    onClick={() => {
                      if (confirm(`Vymazať skupinu "${group.label}"?`)) deleteGroup(group.name)
                    }}
                    disabled={deleting === group.name}
                    className="text-xs text-red-400 hover:text-red-600 px-2 py-1 rounded hover:bg-red-50 transition-colors disabled:opacity-40"
                  >
                    {deleting === group.name ? '...' : 'Zmazať'}
                  </button>
                )}
                <span className={`text-gray-400 text-xs transition-transform ${expanded === group.name ? 'rotate-180' : ''}`}
                  onClick={() => setExpanded(expanded === group.name ? null : group.name)}>▼</span>
              </div>
            </div>

            {expanded === group.name && (
              <div className="border-t border-gray-50">
                {group.members.length === 0 ? (
                  <div className="px-4 py-4 text-xs text-gray-400 text-center">Žiadni členovia</div>
                ) : (
                  <div className="divide-y divide-gray-50">
                    {group.members.map((member) => (
                      <MemberRow
                        key={member.username}
                        member={member}
                        currentGroup={group.name}
                        groups={groups}
                        moving={moving === member.username}
                        onMove={(newGroup) => moveUser(member.username, newGroup)}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {showCreate && (
        <CreateGroupModal
          onClose={() => setShowCreate(false)}
          onCreated={(g) => {
            setGroups((prev) => [...prev, g])
            setShowCreate(false)
          }}
        />
      )}
    </div>
  )
}

function MemberRow({
  member,
  currentGroup,
  groups,
  moving,
  onMove,
}: {
  member: LDAPUser
  currentGroup: string
  groups: GroupInfo[]
  moving: boolean
  onMove: (group: string) => void
}) {
  return (
    <div className="flex items-center justify-between px-4 py-2.5 gap-3">
      <div className="min-w-0">
        <div className="text-sm text-gray-800 truncate">
          {member.full_name || member.username}
          {member.disabled && (
            <span className="ml-1.5 text-xs bg-red-100 text-red-500 px-1 py-0.5 rounded">zakázaný</span>
          )}
        </div>
        <div className="text-xs text-gray-400 truncate">{member.username}</div>
      </div>
      <select
        value={currentGroup}
        onChange={(e) => onMove(e.target.value)}
        disabled={moving}
        className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 text-gray-600 bg-white disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {groups.map((g) => (
          <option key={g.name} value={g.name}>{g.label}</option>
        ))}
      </select>
    </div>
  )
}

function CreateGroupModal({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (group: GroupInfo) => void
}) {
  const [name, setName] = useState('')
  const [label, setLabel] = useState('')
  const [vlan, setVlan] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      const group = await api.post<GroupInfo>('/users/groups/', {
        name: name.trim(),
        label: label.trim(),
        vlan: parseInt(vlan, 10),
      })
      onCreated(group)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Chyba')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-base font-bold text-gray-900 mb-4">Nová skupina</h2>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="text-xs font-medium text-gray-600 block mb-1">Názov (slug)</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="napr. lektori"
              pattern="[a-z0-9_-]+"
              required
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-400 mt-0.5">len malé písmená, číslice, _ a -</p>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 block mb-1">Zobrazovaný názov</label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="napr. Lektori"
              required
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 block mb-1">VLAN</label>
            <input
              type="number"
              value={vlan}
              onChange={(e) => setVlan(e.target.value)}
              placeholder="napr. 20"
              min={1}
              max={4094}
              required
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {error && <p className="text-xs text-red-500">{error}</p>}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-gray-200 text-gray-600 text-sm py-2 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Zrušiť
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-sm py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              {saving ? 'Ukladám...' : 'Vytvoriť'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
