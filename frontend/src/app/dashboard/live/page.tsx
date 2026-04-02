'use client'

import { useState, useEffect, useRef } from 'react'
import { api, type RadiusSession } from '@/lib/api'
import { formatRelative, formatDuration } from '@/lib/utils'

const REFRESH_INTERVAL = 15

export default function LivePage() {
  const [sessions, setSessions] = useState<RadiusSession[]>([])
  const [loading, setLoading] = useState(true)
  const [disconnecting, setDisconnecting] = useState<string | null>(null)
  const [disconnectConfirm, setDisconnectConfirm] = useState<string | null>(null)
  const [countdown, setCountdown] = useState(REFRESH_INTERVAL)
  const countdownRef = useRef(REFRESH_INTERVAL)

  function load() {
    api.get<RadiusSession[]>('/sessions/live/').then(setSessions).finally(() => setLoading(false))
    countdownRef.current = REFRESH_INTERVAL
    setCountdown(REFRESH_INTERVAL)
  }

  useEffect(() => {
    load()
    const refreshInterval = setInterval(load, REFRESH_INTERVAL * 1000)
    const tickInterval = setInterval(() => {
      countdownRef.current = Math.max(0, countdownRef.current - 1)
      setCountdown(countdownRef.current)
    }, 1000)
    return () => {
      clearInterval(refreshInterval)
      clearInterval(tickInterval)
    }
  }, [])

  async function disconnect(sessionId: string) {
    setDisconnectConfirm(null)
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
            {loading
              ? 'Načítavam...'
              : `${sessions.length} aktívnych · `}
            {!loading && (
              <span className={countdown <= 5 ? 'text-blue-500' : ''}>
                obnova za {countdown}s
              </span>
            )}
          </p>
        </div>
        <button
          onClick={load}
          className="text-sm text-gray-500 hover:text-gray-700 px-3 py-2 rounded-lg hover:bg-gray-100"
          style={{ minHeight: 44 }}
        >
          🔄 Obnoviť
        </button>
      </div>

      {loading ? (
        <div className="bg-white rounded-xl border border-gray-100 overflow-hidden divide-y divide-gray-50">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="px-4 py-3 flex items-start gap-3">
              <div className="skeleton w-2 h-2 rounded-full mt-2 flex-shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="skeleton h-3.5 w-36" />
                <div className="skeleton h-3 w-56" />
                <div className="skeleton h-3 w-44" />
              </div>
            </div>
          ))}
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
                    {/* Row 1: username + SSID */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm text-gray-900">{s.username}</span>
                      <span className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded flex-shrink-0">{s.ssid || 'Oratko'}</span>
                    </div>
                    {/* Row 2: IP · AP · MAC */}
                    <div className="mt-1 text-xs text-gray-400 flex flex-wrap gap-x-3 gap-y-0.5">
                      <span className="truncate max-w-[120px]">IP: {s.framed_ip_address || '–'}</span>
                      <span className="truncate max-w-[140px]">AP: {s.nas_identifier || s.ap_mac || '–'}</span>
                      <span className="truncate max-w-[130px]">MAC: {s.calling_station_id || '–'}</span>
                    </div>
                    {/* Row 3: time info + data */}
                    <div className="mt-0.5 text-xs text-gray-400 flex flex-wrap gap-x-3 gap-y-0.5">
                      <span>Pripojený: {s.acct_start_time ? formatRelative(s.acct_start_time) : '–'}</span>
                      <span>Trvanie: {formatDuration(s.acct_session_time)}</span>
                      <span>{s.download_mb}↓ / {s.upload_mb}↑ MB</span>
                    </div>
                  </div>
                  {disconnectConfirm === s.acct_session_id ? (
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button onClick={() => disconnect(s.acct_session_id)} className="text-xs px-2 py-1 bg-red-600 text-white rounded-lg hover:bg-red-700">Áno</button>
                      <button onClick={() => setDisconnectConfirm(null)} className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200">Nie</button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDisconnectConfirm(s.acct_session_id)}
                      disabled={disconnecting === s.acct_session_id}
                      className="flex-shrink-0 text-xs px-3 py-1.5 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg disabled:opacity-50 transition-colors"
                    >
                      {disconnecting === s.acct_session_id ? '...' : 'Odpojiť'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
