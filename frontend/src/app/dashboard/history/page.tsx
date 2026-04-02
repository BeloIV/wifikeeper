'use client'

import { useState, useEffect, useCallback } from 'react'
import { api, type RadiusSession } from '@/lib/api'
import { formatDate, formatDuration } from '@/lib/utils'

type PaginatedResponse<T> = {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export default function HistoryPage() {
  const [data, setData] = useState<PaginatedResponse<RadiusSession> | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [showSearch, setShowSearch] = useState(false)
  const [filters, setFilters] = useState({
    search: '',
    date_from: '',
    date_to: '',
  })

  const load = useCallback(() => {
    setLoading(true)
    const params = new URLSearchParams({ page: String(page) })
    if (filters.search) params.set('search', filters.search)
    if (filters.date_from) params.set('date_from', filters.date_from)
    if (filters.date_to) params.set('date_to', filters.date_to)
    api.get<PaginatedResponse<RadiusSession>>(`/sessions/history/?${params}`)
      .then(setData)
      .finally(() => setLoading(false))
  }, [page, filters])

  useEffect(() => { load() }, [load])

  function applyFilters(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    load()
  }

  return (
    <div className="space-y-4 max-w-5xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">História pripojení</h1>
        <button
          onClick={() => setShowSearch(!showSearch)}
          title="Hľadať a filtrovať"
          className={`relative btn-icon border transition-colors ${
            showSearch || filters.search || filters.date_from || filters.date_to
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-200 text-gray-500 hover:bg-gray-50'
          }`}
        >
          <span>🔍</span>
          {(filters.search || filters.date_from || filters.date_to) && (
            <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-blue-600" />
          )}
        </button>
      </div>

      {/* Filtre */}
      {showSearch && (
        <form onSubmit={applyFilters} className="bg-white rounded-xl border border-gray-100 p-4 space-y-2">
          <input
            type="search"
            placeholder="Hľadať – meno, login, MAC adresa, IP..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="input"
          />
          <div className="flex flex-wrap gap-2 items-center">
            <input
              type="date"
              value={filters.date_from}
              onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
              className="input flex-1"
              title="Dátum od"
            />
            <span className="text-gray-400 text-sm flex-shrink-0">–</span>
            <input
              type="date"
              value={filters.date_to}
              onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
              className="input flex-1"
              title="Dátum do"
            />
            <button type="submit" className="bg-blue-600 text-white text-sm py-2.5 px-4 rounded-lg hover:bg-blue-700 flex-shrink-0" style={{ minHeight: 44 }}>
              Hľadať
            </button>
          </div>
        </form>
      )}

      {/* Výsledky */}
      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="divide-y divide-gray-50">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="px-4 py-3 flex items-start gap-3">
                <div className="skeleton w-2 h-2 rounded-full mt-2 flex-shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="skeleton h-3.5 w-40" />
                  <div className="skeleton h-3 w-64" />
                  <div className="skeleton h-3 w-48" />
                </div>
              </div>
            ))}
          </div>
        ) : !data || data.results.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">Žiadne záznamy</div>
        ) : (
          <>
            <div className="px-4 py-3 border-b border-gray-50 flex items-center justify-between">
              <span className="text-sm text-gray-500">{data.count} záznamov celkom</span>
            </div>
            <div className="divide-y divide-gray-50">
              {data.results.map((s) => (
                <div key={s.id} className="px-4 py-3">
                  <div className="flex items-start gap-3">
                    <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                      s.is_active ? 'bg-green-400' : 'bg-gray-300'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-sm text-gray-900">{s.username}</span>
                        <span className="text-xs text-gray-400">{s.ssid || s.called_station_id}</span>
                        {s.is_active && (
                          <span className="text-xs bg-green-50 text-green-600 px-1.5 py-0.5 rounded">aktívny</span>
                        )}
                      </div>
                      <div className="mt-1 grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-0.5 text-xs text-gray-400">
                        <span>Začiatok: {formatDate(s.acct_start_time)}</span>
                        <span>Koniec: {s.acct_stop_time ? formatDate(s.acct_stop_time) : '–'}</span>
                        <span>Trvanie: {formatDuration(s.acct_session_time)}</span>
                        <span>IP: {s.framed_ip_address || '–'}</span>
                        <span>AP: {s.nas_identifier || s.ap_mac || '–'}</span>
                        <span>{s.download_mb}↓ / {s.upload_mb}↑ MB</span>
                      </div>
                      {s.acct_terminate_cause && (
                        <div className="text-xs text-gray-300 mt-0.5">Ukončené: {s.acct_terminate_cause}</div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Stránkovanie */}
            <div className="px-4 py-3 border-t border-gray-50 flex items-center justify-between gap-2">
              <button
                disabled={!data.previous}
                onClick={() => setPage(page - 1)}
                className="text-sm px-4 py-2.5 rounded-lg hover:bg-gray-100 disabled:opacity-40"
                style={{ minHeight: 44 }}
              >
                ← Späť
              </button>
              <span className="text-xs text-gray-400">
                Strana {page} z {Math.ceil(data.count / 20) || 1}
              </span>
              <button
                disabled={!data.next}
                onClick={() => setPage(page + 1)}
                className="text-sm px-4 py-2.5 rounded-lg hover:bg-gray-100 disabled:opacity-40"
                style={{ minHeight: 44 }}
              >
                Ďalej →
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
