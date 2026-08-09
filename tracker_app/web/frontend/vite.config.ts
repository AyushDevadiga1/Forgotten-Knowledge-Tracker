import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
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
            // WebSocket transport for the micro-quiz push (Socket.IO)
            '/socket.io': { target: 'http://127.0.0.1:5000', ws: true },
        },
    },
})
