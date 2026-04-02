'use client'

import { useEffect, useState } from 'react'
import { api, type RadiusSession } from '@/lib/api'

type Stats = {
  live: number
  users_total: number
  keys_active: number
}

export default function DashboardPage() {
  const [live, setLive] = useState<RadiusSession[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<RadiusSession[]>('/sessions/live/').then(setLive).finally(() => setLoading(false))

    // Auto-refresh každých 30 sekúnd
    const interval = setInterval(() => {
      api.get<RadiusSession[]>('/sessions/live/').then(setLive)
    }, 30_000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Prehľad</h1>
        <p className="text-sm text-gray-500 mt-1">WiFi sieť Oratko </p>
      </div>

  
      

      {/* Live tabuľka */}
      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-50 flex items-center justify-between">
          <h2 className="font-medium text-gray-900">Práve pripojení ({loading ? '…' : String(live.length)})</h2>
          <span className="text-xs text-gray-400">Aktualizuje sa každých 30s</span>
        </div>
        {loading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Načítavam...</div>
        ) : live.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">Žiadne aktívne pripojenia</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {live.slice(0, 10).map((s) => (
              <div key={s.id} className="px-4 py-3 flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-gray-900 truncate">{s.username}</div>
                  <div className="text-xs text-gray-400 truncate">
                    {s.framed_ip_address} · {s.ssid} · {s.nas_identifier || s.ap_mac}
                  </div>
                </div>
                <div className="text-xs text-gray-400 flex-shrink-0 hidden sm:block">
                  {s.download_mb}↓ / {s.upload_mb}↑ MB
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    purple: 'bg-purple-50 text-purple-700',
  }
  return (
    <div className={`rounded-xl p-4 ${colors[color]}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs mt-1 opacity-75">{label}</div>
    </div>
  )
}
