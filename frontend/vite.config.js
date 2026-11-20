import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
  plugins: [
    vue(),
    process.env.NODE_ENV !== 'production' && vueDevTools(),
  ].filter(Boolean),
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) }
  },
  server: {
    // `npm run dev`: forward API calls to the backend (uvicorn on port 8000).
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})