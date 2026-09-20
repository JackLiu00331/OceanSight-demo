// Fixtures that copy the response shapes in PM Plan 3.5. Used only when VITE_API_BASE=mock.
// BUOY-05 has no data on purpose, to exercise the empty state.

const BASE_TIME = Date.parse('2026-10-09T15:00:05Z')

const ROSTER = [
  { buoy_id: 'BUOY-01', name: 'Monterey Offshore', location_lat: 36.8, location_lng: -122.5, temperature: 14.0, pressure: 15.0 },
  { buoy_id: 'BUOY-02', name: 'Point Conception Offshore', location_lat: 34.3, location_lng: -120.9, temperature: 16.5, pressure: 18.0 },
  { buoy_id: 'BUOY-03', name: 'San Diego Offshore', location_lat: 32.9, location_lng: -117.9, temperature: 18.5, pressure: 20.0 },
  { buoy_id: 'BUOY-04', name: 'Cape Mendocino Offshore', location_lat: 40.4, location_lng: -124.6, temperature: 12.5, pressure: 22.0 },
  { buoy_id: 'BUOY-05', name: 'Point Reyes Offshore', location_lat: 38.0, location_lng: -123.5, temperature: 13.5, pressure: 17.0 },
]

const stamp = (ms) => new Date(ms).toISOString().replace('.000Z', 'Z')

// Oldest first, 5 s apart, ending at BASE_TIME. A slow wave keeps the charts from being flat.
function series(buoy, count) {
  if (buoy.buoy_id === 'BUOY-05') return []
  return Array.from({ length: count }, (_, i) => {
    const age = count - 1 - i
    return {
      id: 1000 + i,
      timestamp: stamp(BASE_TIME - age * 5000),
      temperature: Number((buoy.temperature + 0.6 * Math.sin(i / 6)).toFixed(2)),
      pressure: Number((buoy.pressure + 0.4 * Math.cos(i / 8)).toFixed(2)),
      out_of_range: false,
      out_of_range_fields: [],
    }
  })
}

export const mockBuoys = ROSTER.map((buoy) => {
  const history = series(buoy, 50)
  return {
    buoy_id: buoy.buoy_id,
    name: buoy.name,
    status: 'active',
    location_lat: buoy.location_lat,
    location_lng: buoy.location_lng,
    latest_reading: history.length ? history[history.length - 1] : null,
  }
})

export function mockReadings(buoyId, limit = 50) {
  const buoy = ROSTER.find((b) => b.buoy_id === buoyId)
  return buoy ? series(buoy, 50).slice(-limit) : []
}
