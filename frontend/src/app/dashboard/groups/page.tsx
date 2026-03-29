'use client'

import { useState, useEffect, useCallback } from 'react'
import { api, type GroupInfo, type LDAPUser, GROUPS, GROUP_LABELS } from '@/lib/api'

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
      // Optimistic update
      setGroups((prev) => {
        const next = prev.map((g) => ({
          ...g,
          members: g.members.filter((m) => m.username !== username),
          member_count: g.members.some((m) => m.username !== username)
            ? g.member_count
            : g.member_count - (g.members.some((m) => m.username === username) ? 1 : 0),
        }))
        // Add user to new group
        const user = prev
          .flatMap((g) => g.members)
          .find((m) => m.username === username)
        if (user) {
          return next.map((g) =>
            g.name === newGroup
              ? { ...g, members: [...g.members, { ...user, group: newGroup }], member_count: g.member_count + 1 }
              : g,
          )
        }
        return next
      })
    } catch {
      load()
    } finally {
      setMoving(null)
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-gray-400 text-sm">Načítavam skupiny...</div>
  }

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Skupiny</h1>
        <span className="text-sm text-gray-400">{groups.reduce((s, g) => s + g.member_count, 0)} používateľov celkom</span>
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
              <span className={`text-gray-400 text-xs transition-transform ${expanded === group.name ? 'rotate-180' : ''}`}>▼</span>
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
    </div>
  )
}

function MemberRow({
  member,
  currentGroup,
  moving,
  onMove,
}: {
  member: LDAPUser
  currentGroup: string
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
        {GROUPS.map((g) => (
          <option key={g} value={g}>{GROUP_LABELS[g]?.split(' –')[0] ?? g}</option>
        ))}
      </select>
    </div>
  )
}
