import { resolve } from 'path'
import { defineConfig } from 'electron-vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  main: {},
  preload: {},
  renderer: {
    resolve: {
      alias: {
        '@renderer': resolve('src/renderer/src'),
        '@': resolve('../../packages/ui/src')
      }
    },
    optimizeDeps: {
      include: ['@minidrive/shared']
    },
    plugins: [react(), tailwindcss()]
  }
})
