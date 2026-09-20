# frontend/ — Vue 3 dashboard

Vue 3 + Vite, with Chart.js (via vue-chartjs) for the charts. It reads the server's API (`../../OceanSight_PM_Plan.md` §3.5). Needs Node 20.19+ or 22.12+.

## Run

From `OceanSight/`:

```
npm --prefix frontend install       # once
npm --prefix frontend run dev       # http://localhost:5173
npm --prefix frontend run dev:mock  # http://localhost:5174, on fixtures: no server needed
npm --prefix frontend run build     # checks that it compiles
```

Open it as `http://localhost:5173`: Vite listens on `localhost` only, so `127.0.0.1:5173` does not connect. The port is fixed at 5173 because the server only allows that origin (CORS). The page reads `http://127.0.0.1:8000` unless `VITE_API_BASE` says otherwise (see `.env.example`). It uses `127.0.0.1` rather than `localhost` because on Windows `localhost` tries IPv6 first, which slows every new connection.

## What it does

- Lists the buoys with their latest reading and time.
- Select a buoy: latest temperature, pressure and recorded time (local and UTC), two trend charts, and a table of its last 50 readings.
- A buoy without data shows "No current reading available".
- If the server cannot be reached, a banner says so and the page keeps what it had; "Try again" reloads.
- **Refresh** reloads everything. Automatic refresh comes in Sprint R1-4 (FE-7), the map in R1-3 (FE-4), the "request update" button in R1-3 (FE-5), and highlighting of out-of-range readings in R1-3 (FE-6).

## Files

| File | What |
|---|---|
| `src/App.vue` | Loading, the selected buoy, the error banner. |
| `src/components/BuoyList.vue` | The list on the left. |
| `src/components/BuoyDetail.vue` | The cards, charts and table for one buoy. |
| `src/components/TrendChart.vue` | One line chart. |
| `src/api.js` | The two requests, and the error handling. |
| `src/format.js` | Time and number formatting. |
| `src/mock/fixtures.js` | Fixtures in the shape of PM Plan §3.5. BUOY-05 has no data on purpose, to show the empty state. |
| `.env.mock` | Makes `npm run dev:mock` use the fixtures. |
