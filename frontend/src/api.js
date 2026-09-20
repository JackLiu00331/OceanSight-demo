// Talks to the server (PM Plan 3.5). Set VITE_API_BASE=mock to run on the fixtures in ./mock instead.
import { mockBuoys, mockReadings } from './mock/fixtures.js'

// 127.0.0.1, not localhost: on Windows "localhost" tries IPv6 first and every new connection pays for it.
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
export const USING_MOCK = API_BASE === 'mock'

async function request(path) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`)
  } catch {
    throw new Error(`Could not reach the server at ${API_BASE}. Is it running?`)
  }
  if (!response.ok) {
    // Every error from the server has the body {"status": "error", "message": "..."}.
    const body = await response.json().catch(() => null)
    throw new Error(body?.message ?? `The server answered ${response.status}.`)
  }
  return response.json()
}

export const getBuoys = () => (USING_MOCK ? Promise.resolve(mockBuoys) : request('/api/buoys'))

export const getReadings = (buoyId, limit = 50) =>
  USING_MOCK
    ? Promise.resolve(mockReadings(buoyId, limit))
    : request(`/api/buoys/${encodeURIComponent(buoyId)}/data?limit=${limit}`)
