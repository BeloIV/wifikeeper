'use client'

import { useState, useEffect } from 'react'
import { api, type RadiusSession } from '@/lib/api'
import { formatRelative, formatDuration } from '@/lib/utils'

export default function LivePage() {
  const [sessions, setSessions] = useState<RadiusSession[]>([])
  const [loading, setLoading] = useState(true)
  const [disconnecting, setDisconnecting] = useState<string | null>(null)

  function load() {
    api.get<RadiusSession[]>('/sessions/live/').then(setSessions).finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 15_000)
    return () => clearInterval(interval)
  }, [])

  async function disconnect(sessionId: string, username: string) {
    if (!confirm(`Odpojiť používateľa ${username}?`)) return
    setDisconnecting(sessionId)
    try {
      await api.post(`/sessions/live/${sessionId}/disconnect/`, {})
      setTimeout(load, 2000)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Chyba pri odpojení')
    } finally {
      setDisconnecting(null)
    }
  }

  return (
    <div className="space-y-4 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Live pripojenia</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {loading ? 'Načítavam...' : `${sessions.length} aktívnych · aktualizuje sa každých 15s`}
          </p>
        </div>
        <button onClick={load} className="text-sm text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-100">
          🔄 Obnoviť
        </button>
      </div>

      {loading ? (
        <div className="bg-white rounded-xl border border-gray-100 p-8 text-center text-gray-400 text-sm">
          Načítavam...
        </div>
      ) : sessions.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 p-8 text-center text-gray-400 text-sm">
          Žiadne aktívne pripojenia
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
          <div className="divide-y divide-gray-50">
            {sessions.map((s) => (
              <div key={s.id} className="px-4 py-3">
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-green-400 mt-2 flex-shrink-0 animate-pulse" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm text-gray-900">{s.username}</span>
                      <span className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">{s.ssid || 'Oratko'}</span>
                    </div>
                    <div className="mt-1 grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-0.5 text-xs text-gray-400">
                      <span>IP: {s.framed_ip_address || '–'}</span>
                      <span>AP: {s.nas_identifier || s.ap_mac || '–'}</span>
                      <span>MAC: {s.calling_station_id || '–'}</span>
                      <span>Pripojený: {s.acct_start_time ? formatRelative(s.acct_start_time) : '–'}</span>
                      <span>Trvanie: {formatDuration(s.acct_session_time)}</span>
                      <span>{s.download_mb}↓ / {s.upload_mb}↑ MB</span>
                    </div>
                  </div>
                  <button
                    onClick={() => disconnect(s.acct_session_id, s.username)}
                    disabled={disconnecting === s.acct_session_id}
                    className="flex-shrink-0 text-xs px-3 py-1.5 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg disabled:opacity-50 transition-colors"
                  >
                    {disconnecting === s.acct_session_id ? '...' : 'Odpojiť'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
