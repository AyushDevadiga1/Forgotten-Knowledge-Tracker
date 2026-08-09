/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                border: "hsl(var(--border) / <alpha-value>)",
                input: "hsl(var(--input) / <alpha-value>)",
                ring: "hsl(var(--ring) / <alpha-value>)",
                background: "hsl(var(--background) / <alpha-value>)",
                foreground: "hsl(var(--foreground) / <alpha-value>)",
                primary: {
                    DEFAULT: "hsl(var(--primary) / <alpha-value>)",
                    foreground: "hsl(var(--primary-foreground) / <alpha-value>)",
                },
                secondary: {
                    DEFAULT: "hsl(var(--secondary) / <alpha-value>)",
                    foreground: "hsl(var(--secondary-foreground) / <alpha-value>)",
                },
                destructive: {
                    DEFAULT: "hsl(var(--destructive) / <alpha-value>)",
                    foreground: "hsl(var(--destructive-foreground) / <alpha-value>)",
                },
                muted: {
                    DEFAULT: "hsl(var(--muted) / <alpha-value>)",
                    foreground: "hsl(var(--muted-foreground) / <alpha-value>)",
                },
                accent: {
                    DEFAULT: "hsl(var(--accent) / <alpha-value>)",
                    foreground: "hsl(var(--accent-foreground) / <alpha-value>)",
                },
                popover: {
                    DEFAULT: "hsl(var(--popover) / <alpha-value>)",
                    foreground: "hsl(var(--popover-foreground) / <alpha-value>)",
                },
                card: {
                    DEFAULT: "hsl(var(--card) / <alpha-value>)",
                    foreground: "hsl(var(--card-foreground) / <alpha-value>)",
                },
                // FKT identity palette (kept alongside the shadcn tokens)
                'fkt-base': '#0D1117',
                'fkt-surface': '#0F172A',
                'fkt-elevated': '#1E293B',
                'fkt-text-primary': '#F1F5F9',
                'fkt-text-muted': '#64748B',
                'fkt-text-dim': '#334155',
                'fkt-border': '#1E293B',
                'fkt-accent': '#00FFA3',
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
            fontFamily: {
                mono: ['"IBM Plex Mono"', 'monospace'],
                sans: ['"DM Sans"', 'sans-serif'],
            },
            boxShadow: {
                'fkt-glow-sm': '0 0 8px rgba(0, 255, 163, 0.25)',
                'fkt-glow': '0 0 16px rgba(0, 255, 163, 0.35)',
                'fkt-glow-lg': '0 0 32px rgba(0, 255, 163, 0.45)',
            },
            keyframes: {
                "fade-in": {
                    from: { opacity: "0" },
                    to: { opacity: "1" },
                },
                "fade-out": {
                    from: { opacity: "1" },
                    to: { opacity: "0" },
                },
                "slide-in-from-bottom": {
                    from: { transform: "translateY(8px)", opacity: "0" },
                    to: { transform: "translateY(0)", opacity: "1" },
                },
                "slide-out-to-bottom": {
                    from: { transform: "translateY(0)", opacity: "1" },
                    to: { transform: "translateY(8px)", opacity: "0" },
                },
                "slide-in-from-right": {
                    from: { transform: "translateX(12px)", opacity: "0" },
                    to: { transform: "translateX(0)", opacity: "1" },
                },
                "blink-cursor": {
                    "0%, 49%": { opacity: "1" },
                    "50%, 100%": { opacity: "0" },
                },
            },
            animation: {
                "fade-in": "fade-in 0.2s ease-out",
                "fade-out": "fade-out 0.2s ease-out",
                "slide-in-from-bottom": "slide-in-from-bottom 0.3s ease-out",
                "slide-out-to-bottom": "slide-out-to-bottom 0.3s ease-out",
                "slide-in-from-right": "slide-in-from-right 0.3s ease-out",
                "blink-cursor": "blink-cursor 1s step-end infinite",
            },
        },
    },
    plugins: [],
}
