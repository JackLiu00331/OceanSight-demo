<script setup>
import { fixed, formatTime } from '../format.js'

defineProps({
  buoys: { type: Array, required: true },
  selectedId: { type: String, default: null },
})
defineEmits(['select'])
</script>

<template>
  <ul class="buoy-list">
    <li v-for="buoy in buoys" :key="buoy.buoy_id">
      <button
        type="button"
        class="buoy"
        :class="{ selected: buoy.buoy_id === selectedId }"
        @click="$emit('select', buoy.buoy_id)"
      >
        <span class="buoy-name">{{ buoy.name }}</span>
        <span class="buoy-id">{{ buoy.buoy_id }}</span>
        <span v-if="buoy.latest_reading" class="buoy-latest">
          {{ fixed(buoy.latest_reading.temperature, 1) }} °C · {{ fixed(buoy.latest_reading.pressure, 1) }} dbar
          <small>{{ formatTime(buoy.latest_reading.timestamp) }}</small>
        </span>
        <span v-else class="buoy-latest muted">No data yet</span>
      </button>
    </li>
  </ul>
</template>
