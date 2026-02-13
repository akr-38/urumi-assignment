import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcs from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcs()],
})
