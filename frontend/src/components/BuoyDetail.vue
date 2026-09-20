<script setup>
import { computed } from 'vue'
import { fixed, formatLat, formatLng, formatLocal, formatUtc } from '../format.js'
import TrendChart from './TrendChart.vue'

const props = defineProps({
  buoy: { type: Object, required: true },
  readings: { type: Array, required: true }, // oldest first, as the server sends them
})

const latest = computed(() => props.buoy.latest_reading)
const newestFirst = computed(() => [...props.readings].reverse())
const temperaturePoints = computed(() => props.readings.map((r) => ({ timestamp: r.timestamp, value: r.temperature })))
const pressurePoints = computed(() => props.readings.map((r) => ({ timestamp: r.timestamp, value: r.pressure })))
</script>

<template>
  <section class="detail">
    <header class="detail-head">
      <div>
        <h2>{{ buoy.name }}</h2>
        <p class="muted">{{ buoy.buoy_id }} · {{ formatLat(buoy.location_lat) }}, {{ formatLng(buoy.location_lng) }}</p>
      </div>
      <span class="status" :class="buoy.status">{{ buoy.status }}</span>
    </header>

    <div v-if="!latest" class="empty">
      <strong>No current reading available</strong>
      <p>This buoy has not reported any data yet.</p>
    </div>

    <template v-else>
      <div class="stats">
        <div class="card stat">
          <span class="stat-label">Temperature</span>
          <span class="stat-value">{{ fixed(latest.temperature) }}<small> °C</small></span>
        </div>
        <div class="card stat">
          <span class="stat-label">Pressure</span>
          <span class="stat-value">{{ fixed(latest.pressure) }}<small> dbar</small></span>
        </div>
        <div class="card stat">
          <span class="stat-label">Recorded at</span>
          <span class="stat-time">{{ formatLocal(latest.timestamp) }}</span>
          <small class="muted">{{ formatUtc(latest.timestamp) }}</small>
        </div>
      </div>

      <div class="charts">
        <TrendChart title="Temperature" unit="°C" color="#e4572e" :points="temperaturePoints" />
        <TrendChart title="Pressure" unit="dbar" color="#1b6ca8" :points="pressurePoints" />
      </div>

      <div class="card">
        <h3>Recent readings <small class="muted">(last {{ readings.length }}, newest first)</small></h3>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Recorded (UTC)</th>
                <th class="num">Temperature (°C)</th>
                <th class="num">Pressure (dbar)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="reading in newestFirst" :key="reading.id">
                <td>{{ formatUtc(reading.timestamp) }}</td>
                <td class="num">{{ fixed(reading.temperature) }}</td>
                <td class="num">{{ fixed(reading.pressure) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </section>
</template>
