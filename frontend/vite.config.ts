import { fileURLToPath, URL } from 'node:url'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Read version from package.json for injection
const pkgPath = resolve(fileURLToPath(import.meta.url), '../package.json')
const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8')) as { version: string }

// https://vite.dev/config/
export default defineConfig({
  cacheDir: `.vite-cache-${process.pid}`,
  define: {
    __ZHANGSHU_APP_VERSION__: JSON.stringify(pkg.version),
    // Override API base URL to use Vite proxy (routes via dev server to port 8001).
    // This avoids the zombie process on port 8000 that holds old backend code.
    'import.meta.env.VITE_API_BASE_URL': JSON.stringify(''),
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(pkg.version),
  },
  plugins: [
    vue(),
  ],
  server: {
    port: 5180,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
