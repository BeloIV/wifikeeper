'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { api, type User } from '@/lib/api'
import { formatDate } from '@/lib/utils'

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const output = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i++) {
    output[i] = rawData.charCodeAt(i)
  }
  return output
}

function isStandalone(): boolean {
  if (typeof window === 'undefined') return false
  const nav = window.navigator as Navigator & { standalone?: boolean }
  return window.matchMedia('(display-mode: standalone)').matches || nav.standalone === true
}

function isIOS(): boolean {
  if (typeof window === 'undefined') return false
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent)
}

type NotificationStatus = 'firing' | 'resolved' | 'test'

type PushNotificationItem = {
  id: number
  title: string
  body: string
  status: NotificationStatus
  alertname: string
  severity: string
  detail: {
    labels?: Record<string, string>
    annotations?: Record<string, string>
    status?: string
    startsAt?: string
    endsAt?: string
    generatorURL?: string
    note?: string
  }
  created_at: string
  read_at: string | null
}

const STATUS_STYLES: Record<NotificationStatus, string> = {
  firing: 'bg-red-100 text-red-700',
  resolved: 'bg-green-100 text-green-700',
  test: 'bg-gray-100 text-gray-600',
}

const STATUS_LABELS: Record<NotificationStatus, string> = {
  firing: 'Aktívny',
  resolved: 'Vyriešené',
  test: 'Test',
}

function NotificationModal({ item, onClose }: { item: PushNotificationItem; onClose: () => void }) {
  const labels = item.detail?.labels || {}
  const annotations = item.detail?.annotations || {}

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-0 sm:p-4" onClick={onClose}>
      <div
        className="bg-white w-full sm:max-w-lg sm:rounded-2xl rounded-t-2xl max-h-[85vh] overflow-y-auto p-5 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium mb-2 ${STATUS_STYLES[item.status]}`}>
              {STATUS_LABELS[item.status]}
              {item.severity && ` · ${item.severity}`}
            </span>
            <h2 className="text-lg font-semibold text-gray-900">{item.title}</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none px-1">
            ×
          </button>
        </div>

        {item.body && <p className="text-sm text-gray-700">{item.body}</p>}

        <div className="text-xs text-gray-400">{formatDate(item.created_at)}</div>

        {Object.keys(annotations).length > 0 && (
          <div>
            <div className="text-xs font-medium text-gray-500 mb-1.5 uppercase tracking-wide">Detail</div>
            <div className="space-y-1.5">
              {Object.entries(annotations).map(([key, value]) => (
                <div key={key} className="text-sm">
                  <span className="text-gray-500">{key}: </span>
                  <span className="text-gray-800">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {Object.keys(labels).length > 0 && (
          <div>
            <div className="text-xs font-medium text-gray-500 mb-1.5 uppercase tracking-wide">Labels</div>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(labels).map(([key, value]) => (
                <span key={key} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-md">
                  {key}={value}
                </span>
              ))}
            </div>
          </div>
        )}

        {item.detail?.note && <p className="text-sm text-gray-500 italic">{item.detail.note}</p>}
      </div>
    </div>
  )
}

function NotificationsPageInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [authorized, setAuthorized] = useState(false)
  const [supported, setSupported] = useState(true)
  const [needsInstall, setNeedsInstall] = useState(false)
  const [permission, setPermission] = useState<NotificationPermission>('default')
  const [subscribed, setSubscribed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [notifications, setNotifications] = useState<PushNotificationItem[]>([])
  const [selected, setSelected] = useState<PushNotificationItem | null>(null)

  useEffect(() => {
    api.get<User>('/admins/me/').then((u) => {
      if (u.role !== 'superadmin') {
        router.replace('/dashboard')
      } else {
        setAuthorized(true)
      }
    }).catch(() => router.replace('/login'))
  }, [router])

  const refreshState = useCallback(async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
      setSupported(false)
      return
    }
    // iOS Safari podporuje Web Push len z appky pridanej na plochu (standalone).
    // Priamo v Safari tabe subscribe() zlyhá s nezrozumiteľnou chybou.
    if (isIOS() && !isStandalone()) {
      setNeedsInstall(true)
      return
    }
    setPermission(Notification.permission)
    const reg = await navigator.serviceWorker.getRegistration()
    const sub = await reg?.pushManager.getSubscription()
    setSubscribed(!!sub)

    // Heartbeat — potvrdí backendu, že toto zariadenie je stále aktívne, aby
    // ho cleanup task nezmazal ako orphan po zmazaní appky z plochy iného zariadenia.
    if (sub) {
      api.post('/push/heartbeat/', { endpoint: sub.endpoint }).catch(() => {})
    }
  }, [])

  const loadNotifications = useCallback(() => {
    api.get<{ results: PushNotificationItem[] }>('/push/notifications/').then((d) => {
      setNotifications(d.results || [])
    })
  }, [])

  const openNotification = useCallback((id: number) => {
    api.get<PushNotificationItem>(`/push/notifications/${id}/`).then((item) => {
      setSelected(item)
      if (!item.read_at) {
        api.post(`/push/notifications/${id}/read/`).then(() => {
          setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n)))
        }).catch(() => {})
      }
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (authorized) {
      refreshState()
      loadNotifications()
    }
  }, [authorized, refreshState, loadNotifications])

  // Otvorenie appky kliknutím na push notifikáciu (deep link cez ?id=)
  useEffect(() => {
    if (!authorized) return
    const idParam = searchParams.get('id')
    if (idParam) {
      openNotification(Number(idParam))
      router.replace('/dashboard/notifications')
    }
  }, [authorized, searchParams, openNotification, router])

  // Appka je už otvorená na pozadí a používateľ klikne na notifikáciu
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return
    function onMessage(event: MessageEvent) {
      if (event.data?.type === 'wifikeeper-notification-click' && typeof event.data.url === 'string') {
        const url = new URL(event.data.url, window.location.origin)
        const idParam = url.searchParams.get('id')
        if (idParam) openNotification(Number(idParam))
        loadNotifications()
      }
    }
    navigator.serviceWorker.addEventListener('message', onMessage)
    return () => navigator.serviceWorker.removeEventListener('message', onMessage)
  }, [openNotification, loadNotifications])

  async function enable() {
    setLoading(true)
    setError('')
    setMessage('')
    try {
      let perm
      try {
        perm = await Notification.requestPermission()
      } catch (permErr) {
        console.error('Notification.requestPermission zlyhalo:', permErr)
        if (isIOS() && !isStandalone()) {
          setNeedsInstall(true)
          return
        }
        const detail = permErr instanceof Error ? `${permErr.name}: ${permErr.message}` : String(permErr)
        throw new Error(`Prehliadač odmietol žiadosť o povolenie notifikácií (${detail}).`)
      }
      setPermission(perm)
      if (perm !== 'granted') {
        setError('Notifikácie neboli povolené v prehliadači.')
        return
      }

      let reg
      try {
        reg = await navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' })
        await navigator.serviceWorker.ready
      } catch (swErr) {
        console.error('serviceWorker.register zlyhalo:', swErr)
        const detail = swErr instanceof Error ? `${swErr.name}: ${swErr.message}` : String(swErr)
        throw new Error(`Nepodarilo sa zaregistrovať service worker (${detail}).`)
      }

      const { publicKey } = await api.get<{ publicKey: string }>('/push/vapid-public-key/')
      let sub
      try {
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(publicKey).buffer as ArrayBuffer,
        })
      } catch (subErr) {
        // WebKit (Safari) hlási takmer akékoľvek zlyhanie subscribe() ako
        // "The string did not match the expected pattern" — najčastejšia príčina
        // je appka otvorená v Safari tabe namiesto z ikonky na ploche.
        console.error('pushManager.subscribe zlyhalo:', subErr)
        if (isIOS() && !isStandalone()) {
          setNeedsInstall(true)
          return
        }
        const detail = subErr instanceof Error ? `${subErr.name}: ${subErr.message}` : String(subErr)
        throw new Error(
          `Zariadenie/prehliadač odmietol registráciu na notifikácie (${detail}). Skús appku úplne zatvoriť ` +
          `(odstrániť z app switchera) a znova otvoriť z ikonky na ploche.`
        )
      }

      await api.post('/push/subscribe/', sub.toJSON())
      setSubscribed(true)
      setMessage('Notifikácie sú zapnuté.')
    } catch (e) {
      console.error('enable() zlyhalo:', e)
      if (e instanceof Error && e.message.startsWith('Nepodarilo sa') || e instanceof Error && e.message.startsWith('Zariadenie') || e instanceof Error && e.message.startsWith('Prehliadač')) {
        setError(e.message)
      } else {
        const detail = e instanceof Error ? `${e.name}: ${e.message}` : String(e)
        setError(`Nepodarilo sa zapnúť notifikácie — neočakávaná chyba (${detail}). Skús appku zavrieť a znova otvoriť z plochy.`)
      }
    } finally {
      setLoading(false)
    }
  }

  async function disable() {
    setLoading(true)
    setError('')
    setMessage('')
    try {
      const reg = await navigator.serviceWorker.getRegistration()
      const sub = await reg?.pushManager.getSubscription()
      if (sub) {
        await api.post('/push/unsubscribe/', { endpoint: sub.endpoint })
        await sub.unsubscribe()
      }
      setSubscribed(false)
      setMessage('Notifikácie sú vypnuté.')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Nepodarilo sa vypnúť notifikácie.')
    } finally {
      setLoading(false)
    }
  }

  async function sendTest() {
    setLoading(true)
    setError('')
    setMessage('')
    try {
      await api.post('/push/test/')
      setMessage('Testovacia notifikácia odoslaná.')
      loadNotifications()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Odoslanie zlyhalo.')
    } finally {
      setLoading(false)
    }
  }

  if (!authorized) return null

  const compact = subscribed && notifications.length > 0

  return (
    <div className="max-w-xl mx-auto p-4 sm:p-6">
      {compact ? (
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-semibold text-gray-900">Notifikácie</h1>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-xs text-gray-400">Zapnuté</span>
          </div>
        </div>
      ) : (
        <>
          <h1 className="text-xl font-semibold text-gray-900 mb-1">Notifikácie</h1>
          <p className="text-sm text-gray-500 mb-6">
            Push notifikácie priamo do telefónu (Grafana alerty – kontajnery, chyby, CPU/RAM).
            Túto stránku si pridaj na plochu telefónu (Zdieľať → Pridať na plochu), nech to funguje ako appka.
          </p>
        </>
      )}

      {!supported && (
        <div className="rounded-lg bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm p-3 mb-4">
          Tento prehliadač nepodporuje push notifikácie.
        </div>
      )}

      {supported && needsInstall && (
        <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 sm:p-5 space-y-2 mb-6">
          <div className="font-medium text-blue-900">Najprv pridaj appku na plochu</div>
          <p className="text-sm text-blue-800">
            Na iPhone push notifikácie fungujú len z appky pridanej na plochu — nie priamo v Safari.
          </p>
          <ol className="text-sm text-blue-800 list-decimal list-inside space-y-1">
            <li>V Safari klikni na ikonu <strong>Zdieľať</strong> (štvorček so šípkou dole)</li>
            <li>Zvoľ <strong>Pridať na plochu</strong></li>
            <li>Otvor appku z novej ikonky na ploche</li>
            <li>Tu v appke znova choď do Notifikácie → Zapnúť notifikácie</li>
          </ol>
        </div>
      )}

      {supported && !needsInstall && compact && (
        <div className="flex items-center gap-2 mb-6">
          <button
            onClick={sendTest}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg bg-gray-100 text-gray-700 text-xs font-medium hover:bg-gray-200 disabled:opacity-50"
          >
            Test
          </button>
          <button
            onClick={disable}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg bg-gray-100 text-gray-700 text-xs font-medium hover:bg-gray-200 disabled:opacity-50"
          >
            Vypnúť
          </button>
          {message && <span className="text-xs text-green-700">{message}</span>}
          {error && <span className="text-xs text-red-600">{error}</span>}
        </div>
      )}

      {supported && !needsInstall && !compact && (
        <div className="rounded-xl border border-gray-100 bg-white p-4 sm:p-5 space-y-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium text-gray-900">Stav</div>
              <div className="text-sm text-gray-500">
                {subscribed ? 'Zapnuté na tomto zariadení' : 'Vypnuté na tomto zariadení'}
                {permission === 'denied' && ' — povolenie zamietnuté v prehliadači'}
              </div>
            </div>
            <span className={`w-2.5 h-2.5 rounded-full ${subscribed ? 'bg-green-500' : 'bg-gray-300'}`} />
          </div>

          <div className="flex flex-wrap gap-2">
            {!subscribed ? (
              <button
                onClick={enable}
                disabled={loading || permission === 'denied'}
                className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                Zapnúť notifikácie
              </button>
            ) : (
              <>
                <button
                  onClick={sendTest}
                  disabled={loading}
                  className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
                >
                  Odoslať testovaciu notifikáciu
                </button>
                <button
                  onClick={disable}
                  disabled={loading}
                  className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
                >
                  Vypnúť
                </button>
              </>
            )}
          </div>

          {message && <div className="text-sm text-green-700">{message}</div>}
          {error && <div className="text-sm text-red-600">{error}</div>}
        </div>
      )}

      <div>
        <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">História</h2>
        {notifications.length === 0 ? (
          <div className="text-sm text-gray-400 text-center py-8">Zatiaľ žiadne notifikácie.</div>
        ) : (
          <div className="rounded-xl border border-gray-100 bg-white divide-y divide-gray-100 overflow-hidden">
            {notifications.map((n) => (
              <button
                key={n.id}
                onClick={() => openNotification(n.id)}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 flex items-start gap-3"
              >
                {!n.read_at && <span className="w-2 h-2 rounded-full bg-blue-600 mt-1.5 shrink-0" />}
                {n.read_at && <span className="w-2 h-2 shrink-0" />}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${STATUS_STYLES[n.status]}`}>
                      {STATUS_LABELS[n.status]}
                    </span>
                    <span className="font-medium text-gray-900 truncate">{n.title}</span>
                  </div>
                  {n.body && <div className="text-sm text-gray-500 truncate">{n.body}</div>}
                  <div className="text-xs text-gray-400 mt-0.5">{formatDate(n.created_at)}</div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {selected && <NotificationModal item={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

export default function NotificationsPage() {
  return (
    <Suspense fallback={null}>
      <NotificationsPageInner />
    </Suspense>
  )
}
