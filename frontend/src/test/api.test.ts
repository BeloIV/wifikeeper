import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mockujeme window.location
const mockLocation = { href: '' }
Object.defineProperty(window, 'location', { value: mockLocation, writable: true })

// Mockujeme localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

describe('api client', () => {
  beforeEach(() => {
    localStorageMock.clear()
    mockLocation.href = ''
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('login uloží tokeny do localStorage', async () => {
    vi.stubGlobal('fetch', mockFetch(200, {
      access: 'access_token_value',
      refresh: 'refresh_token_value',
      user: { id: 1, username: 'admin', role: 'admin' },
    }))
    const { login } = await import('@/lib/api')
    await login('admin', 'pass')
    expect(localStorageMock.getItem('access_token')).toBe('access_token_value')
    expect(localStorageMock.getItem('refresh_token')).toBe('refresh_token_value')
  })

  it('api.get pripojí Authorization header', async () => {
    localStorageMock.setItem('access_token', 'my_token')
    const fetchMock = mockFetch(200, { data: 'ok' })
    vi.stubGlobal('fetch', fetchMock)
    const { api } = await import('@/lib/api')
    await api.get('/test/')
    const callArgs = fetchMock.mock.calls[0]
    expect(callArgs[1].headers).toMatchObject({ Authorization: 'Bearer my_token' })
  })

  it('api.get presmeruje na /login pri 401', async () => {
    vi.stubGlobal('fetch', mockFetch(401, { detail: 'Unauthorized' }))
    const { api } = await import('@/lib/api')
    await expect(api.get('/protected/')).rejects.toThrow('Unauthorized')
    expect(mockLocation.href).toBe('/login')
  })

  it('api.post posiela JSON body', async () => {
    const fetchMock = mockFetch(201, { id: 1 })
    vi.stubGlobal('fetch', fetchMock)
    const { api } = await import('@/lib/api')
    await api.post('/items/', { name: 'test' })
    const callArgs = fetchMock.mock.calls[0]
    expect(callArgs[1].method).toBe('POST')
    expect(callArgs[1].body).toBe(JSON.stringify({ name: 'test' }))
  })

  it('204 odpoveď vráti undefined', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: () => Promise.reject(new Error('no body')),
    }))
    const { api } = await import('@/lib/api')
    const result = await api.delete('/items/1/')
    expect(result).toBeUndefined()
  })
})
