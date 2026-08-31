/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    // Respect an externally-assigned PORT (e.g. from the dev tooling's
    // port-conflict avoidance) instead of hardcoding 5173 -- the backend's
    // CORS is already configured to accept any localhost/127.0.0.1 port,
    // specifically so the frontend port can float.
    port: Number(process.env.PORT) || 5173,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
