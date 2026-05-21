import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const previewPort = Number(globalThis.process?.env?.PORT || 4173)

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
  },
  preview: {
    host: '0.0.0.0',
    port: previewPort,
  },
})
