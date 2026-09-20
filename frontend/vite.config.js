import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // The server only allows this origin (PM Plan 3.5, CORS), so the port must not drift.
  server: { port: 5173, strictPort: true },
})
