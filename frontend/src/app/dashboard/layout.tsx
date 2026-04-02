'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { api, logout, type User } from '@/lib/api'

const NAV = [
  { href: '/dashboard', label: 'Prehľad', short: 'Prehľad', icon: '🏠' },
  { href: '/dashboard/users', label: 'Používatelia', short: 'Ľudia', icon: '👥' },
  { href: '/dashboard/groups', label: 'Skupiny', short: 'Skupiny', icon: '🗂️' },
  { href: '/dashboard/keys', label: 'Kľúče', short: 'Kľúče', icon: '🔑' },
  { href: '/dashboard/live', label: 'Live', short: 'Live', icon: '📶' },
  { href: '/dashboard/history', label: 'História', short: 'Hist.', icon: '📋' },
  { href: '/dashboard/admins', label: 'Admini', short: 'Admin', icon: '⚙️', superadminOnly: true },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    api.get<User>('/admins/me/').then(setUser).catch(() => {
      router.push('/login')
    })
  }, [router])

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-400 text-sm">Načítavam...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-40">
        <div className="flex items-center justify-between px-4 h-14">
          <span className="font-semibold text-gray-900">WiFi Manager</span>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500 hidden sm:block">
              {user.first_name || user.username}
            </span>
            <button
              onClick={logout}
              className="text-sm text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-100"
            >
              Odhlásiť
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1">
        {/* Sidebar – desktop */}
        <nav className="hidden md:flex flex-col w-56 bg-white border-r border-gray-100 p-3 gap-1">
          {NAV.filter((item) => !item.superadminOnly || user.role === 'superadmin').map((item) => {
            const active = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href))
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <span>{item.icon}</span>
                {item.label}
              </Link>
            )
          })}
        </nav>

        {/* Hlavný obsah */}
        <main className="flex-1 p-4 md:p-6 overflow-auto">
          {children}
        </main>
      </div>

      {/* Bottom nav – mobile */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 flex z-40"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        {NAV.filter((item) => !item.superadminOnly || user.role === 'superadmin').map((item) => {
          const active = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href))
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex-1 flex flex-col items-center justify-center py-1 gap-0.5 ${
                active ? 'text-blue-600' : 'text-gray-400'
              }`}
              style={{ minHeight: 52 }}
            >
              <span className="text-xl leading-none">{item.icon}</span>
              <span style={{ fontSize: 9 }} className="leading-tight font-medium">{item.short}</span>
            </Link>
          )
        })}
      </nav>

      <div className="md:hidden" style={{ height: 'calc(52px + env(safe-area-inset-bottom))' }} />
    </div>
  )
}
