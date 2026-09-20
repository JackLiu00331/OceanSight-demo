<script setup>
import { computed, onMounted, ref } from 'vue'
import { USING_MOCK, getBuoys, getReadings } from './api.js'
import BuoyDetail from './components/BuoyDetail.vue'
import BuoyList from './components/BuoyList.vue'

const buoys = ref([])
const readings = ref([])
const selectedId = ref(null)
const loading = ref(true)
const error = ref('')
const updatedAt = ref(null)

const selected = computed(() => buoys.value.find((b) => b.buoy_id === selectedId.value) ?? null)

let latestRequest = 0 // a slow answer that arrives after a newer request is ignored

async function load() {
  const request = ++latestRequest
  loading.value = true
  try {
    const list = await getBuoys()
    const id = list.some((b) => b.buoy_id === selectedId.value) ? selectedId.value : (list[0]?.buoy_id ?? null)
    const history = id ? await getReadings(id) : []
    if (request !== latestRequest) return
    buoys.value = list
    selectedId.value = id
    readings.value = history
    error.value = ''
    updatedAt.value = new Date()
  } catch (err) {
    if (request !== latestRequest) return
    error.value = err.message
  } finally {
    if (request === latestRequest) loading.value = false
  }
}

function select(id) {
  selectedId.value = id
  load()
}

onMounted(load)
</script>

<template>
  <header class="topbar">
    <div class="brand">
      <span class="logo" aria-hidden="true">◉</span>
      <div>
        <h1>OceanSight</h1>
        <p>Ocean buoy monitoring</p>
      </div>
    </div>
    <div class="topbar-actions">
      <span v-if="USING_MOCK" class="pill">mock data</span>
      <span v-if="updatedAt" class="muted">Updated {{ updatedAt.toLocaleTimeString() }}</span>
      <button type="button" class="button" :disabled="loading" @click="load">
        {{ loading ? 'Loading…' : 'Refresh' }}
      </button>
    </div>
  </header>

  <div v-if="error" class="banner" role="alert">
    <span>{{ error }}</span>
    <button type="button" class="button ghost" @click="load">Try again</button>
  </div>

  <main class="layout">
    <aside>
      <h2 class="section-title">Buoys</h2>
      <BuoyList v-if="buoys.length" :buoys="buoys" :selected-id="selectedId" @select="select" />
      <p v-else-if="loading" class="muted">Loading…</p>
      <p v-else-if="!error" class="muted">No buoys are registered.</p>
    </aside>

    <div class="content">
      <BuoyDetail v-if="selected" :buoy="selected" :readings="readings" />
      <div v-else-if="!loading" class="empty">
        <strong>Nothing to show</strong>
        <p>Buoy data will appear here once the server is reachable.</p>
      </div>
    </div>
  </main>
</template>
