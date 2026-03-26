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
  const [filters, setFilters] = useState({
    username: '',
    ssid: '',
    date_from: '',
    date_to: '',
    search: '',
  })

  const load = useCallback(() => {
    setLoading(true)
    const params = new URLSearchParams({ page: String(page) })
    if (filters.username) params.set('username', filters.username)
    if (filters.ssid) params.set('ssid', filters.ssid)
    if (filters.date_from) params.set('date_from', filters.date_from)
    if (filters.date_to) params.set('date_to', filters.date_to)
    if (filters.search) params.set('search', filters.search)
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
      <h1 className="text-xl font-bold text-gray-900">História pripojení</h1>

      {/* Filtre */}
      <form onSubmit={applyFilters} className="bg-white rounded-xl border border-gray-100 p-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          <input
            type="search"
            placeholder="Hľadať..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="input col-span-2 sm:col-span-1"
          />
          <input
            placeholder="Používateľ"
            value={filters.username}
            onChange={(e) => setFilters({ ...filters, username: e.target.value })}
            className="input"
          />
          <input
            placeholder="SSID"
            value={filters.ssid}
            onChange={(e) => setFilters({ ...filters, ssid: e.target.value })}
            className="input"
          />
          <input
            type="date"
            value={filters.date_from}
            onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
            className="input"
            title="Dátum od"
          />
          <input
            type="date"
            value={filters.date_to}
            onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
            className="input"
            title="Dátum do"
          />
          <button type="submit" className="bg-blue-600 text-white text-sm py-2 px-4 rounded-lg hover:bg-blue-700">
            Filtrovať
          </button>
        </div>
      </form>

      {/* Výsledky */}
      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Načítavam...</div>
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
            <div className="px-4 py-3 border-t border-gray-50 flex items-center justify-between">
              <button
                disabled={!data.previous}
                onClick={() => setPage(page - 1)}
                className="text-sm px-3 py-1.5 rounded-lg hover:bg-gray-100 disabled:opacity-40"
              >
                ← Predchádzajúca
              </button>
              <span className="text-xs text-gray-400">Strana {page}</span>
              <button
                disabled={!data.next}
                onClick={() => setPage(page + 1)}
                className="text-sm px-3 py-1.5 rounded-lg hover:bg-gray-100 disabled:opacity-40"
              >
                Ďalšia →
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
