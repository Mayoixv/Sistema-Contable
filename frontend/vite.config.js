import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// El dev server proxea /api y /health al backend. Gracias a esto el navegador
// ve un solo origen (localhost:5173) y no hace falta configurar CORS en
// FastAPI: en producción el backend sirve el bundle ya compilado, así que
// tampoco ahí hay cruce de orígenes.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8001', changeOrigin: true },
      '/health': { target: 'http://localhost:8001', changeOrigin: true },
    },
  },
})
