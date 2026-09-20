<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import { CategoryScale, Chart as ChartJS, Filler, LinearScale, LineElement, PointElement, Tooltip } from 'chart.js'
import { formatTime } from '../format.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip)

const props = defineProps({
  title: { type: String, required: true },
  unit: { type: String, required: true },
  color: { type: String, required: true },
  points: { type: Array, required: true }, // [{ timestamp, value }], oldest first
})

const data = computed(() => ({
  labels: props.points.map((p) => formatTime(p.timestamp)),
  datasets: [
    {
      data: props.points.map((p) => p.value),
      borderColor: props.color,
      backgroundColor: `${props.color}22`,
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      tension: 0.3,
      fill: true,
    },
  ],
}))

const options = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: (context) => `${context.parsed.y} ${props.unit}` } },
  },
  scales: {
    x: { ticks: { maxTicksLimit: 6, maxRotation: 0 }, grid: { display: false } },
    y: { title: { display: true, text: props.unit }, grace: '10%' },
  },
}))
</script>

<template>
  <div class="card chart-card">
    <h3>{{ title }}</h3>
    <div v-if="points.length" class="chart-box">
      <Line :data="data" :options="options" />
    </div>
    <p v-else class="muted">No readings yet.</p>
  </div>
</template>
