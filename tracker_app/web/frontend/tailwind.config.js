/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'fkt-base': '#0D1117',
                'fkt-surface': '#0F172A',
                'fkt-elevated': '#1E293B',
                'fkt-text-primary': '#F1F5F9',
                'fkt-text-muted': '#64748B',
                'fkt-text-dim': '#334155',
                'fkt-border': '#1E293B',
                'fkt-accent': '#00FFA3',
            },
            fontFamily: {
                mono: ['"IBM Plex Mono"', 'monospace'],
                sans: ['"DM Sans"', 'sans-serif'],
            }
        },
    },
    plugins: [],
}
