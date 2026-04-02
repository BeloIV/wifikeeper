'use client'

import { useState, useRef, useEffect } from 'react'

const VLANS = [
  {
    vlan: 20,
    label: 'Plný prístup',
    desc: 'internet, tlačiarne, AirPlay a všetky lokálne služby',
  },
  {
    vlan: 40,
    label: 'Len internet',
    desc: 'bez tlačiarní a AirPlay',
  },
]

export function VlanInfoButton() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  return (
    <div ref={ref} className="relative inline-flex items-center">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-4 h-4 rounded-full bg-gray-200 text-gray-500 text-[10px] font-bold hover:bg-gray-300 transition-colors flex items-center justify-center leading-none"
        title="Čo znamenajú jednotlivé VLAN?"
      >
        ?
      </button>
      {open && (
        <div className="absolute left-0 top-5 z-[200] w-64 bg-white rounded-xl shadow-lg border border-gray-100 p-3 space-y-2.5">
          {VLANS.map(({ vlan, label, desc }) => (
            <div key={vlan} className="flex gap-2.5">
              <span className="text-xs font-mono font-bold text-blue-600 w-14 flex-shrink-0 pt-0.5">
                VLAN {vlan}
              </span>
              <div>
                <div className="text-xs font-medium text-gray-800">{label}</div>
                <div className="text-xs text-gray-400 mt-0.5">{desc}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
