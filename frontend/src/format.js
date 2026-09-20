// Timestamps arrive as UTC text such as 2026-10-09T15:00:05Z (PM Plan 3.2).

export const fixed = (value, digits = 2) => (value == null ? '—' : Number(value).toFixed(digits))

export const formatUtc = (iso) => iso.replace('T', ' ').replace('Z', ' UTC')

export const formatLocal = (iso) => new Date(iso).toLocaleString()

export const formatTime = (iso) => new Date(iso).toLocaleTimeString()

export const formatLat = (value) => (value == null ? '—' : `${Math.abs(value).toFixed(2)}°${value >= 0 ? 'N' : 'S'}`)

export const formatLng = (value) => (value == null ? '—' : `${Math.abs(value).toFixed(2)}°${value >= 0 ? 'E' : 'W'}`)
