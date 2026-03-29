import { describe, it, expect } from 'vitest'
import { formatDate, formatRelative, formatDuration, formatBytes } from '@/lib/utils'

describe('formatDate', () => {
  it('returns dash for null', () => {
    expect(formatDate(null)).toBe('–')
  })

  it('returns dash for undefined', () => {
    expect(formatDate(undefined)).toBe('–')
  })

  it('formats ISO string in Slovak format', () => {
    // 2024-03-15 14:30 UTC
    const result = formatDate('2024-03-15T14:30:00.000Z')
    // Slovenský formát: d. M. yyyy HH:mm (čas v UTC+localtime, testujeme len formát)
    expect(result).toMatch(/\d{1,2}\. \d{1,2}\. 2024 \d{2}:\d{2}/)
  })

  it('returns dash for empty string', () => {
    expect(formatDate('')).toBe('–')
  })
})

describe('formatDuration', () => {
  it('returns dash for null', () => {
    expect(formatDuration(null)).toBe('–')
  })

  it('returns dash for 0', () => {
    expect(formatDuration(0)).toBe('–')
  })

  it('formats seconds only', () => {
    expect(formatDuration(45)).toBe('45s')
  })

  it('formats minutes and seconds', () => {
    expect(formatDuration(90)).toBe('1m 30s')
  })

  it('formats hours and minutes', () => {
    expect(formatDuration(3661)).toBe('1h 1m')
  })

  it('formats hours without minutes', () => {
    expect(formatDuration(7200)).toBe('2h 0m')
  })
})

describe('formatBytes', () => {
  it('formats 0', () => {
    expect(formatBytes(0)).toBe('0 B')
  })

  it('formats bytes', () => {
    expect(formatBytes(500)).toBe('500 B')
  })

  it('formats kilobytes', () => {
    expect(formatBytes(1024)).toBe('1 KB')
  })

  it('formats megabytes', () => {
    expect(formatBytes(1024 * 1024)).toBe('1 MB')
  })
})
