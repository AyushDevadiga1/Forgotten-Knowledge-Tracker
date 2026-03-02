import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            // All /api/* requests forward to Flask backend
            '/api': {
                target: 'http://127.0.0.1:5000',
                changeOrigin: true,
                secure: false,
            },
            // Also proxy /stats and /search (non-prefixed Flask routes)
            '/stats': { target: 'http://127.0.0.1:5000', changeOrigin: true },
            '/search': { target: 'http://127.0.0.1:5000', changeOrigin: true },
        },
    },
})
