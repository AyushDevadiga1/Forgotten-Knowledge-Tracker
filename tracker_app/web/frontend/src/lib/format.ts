export function formatElapsed(totalSeconds: number | null | undefined): string {
    if (totalSeconds == null) return '00:00'
    const s = Math.max(0, Math.floor(totalSeconds))
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    const sec = s % 60
    const mm = String(m).padStart(2, '0')
    const ss = String(sec).padStart(2, '0')
    return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

export function formatNumber(v: number): string {
    return Math.round(v).toLocaleString()
}

export function formatPercent(v: number): string {
    return `${Math.round(v)}%`
}

export function formatAgo(iso: string): string {
    try {
        const utc = iso.endsWith('Z') ? iso : iso + 'Z'
        const then = new Date(utc).getTime()
        const secs = Math.max(0, Math.round((Date.now() - then) / 1000))
        if (secs < 60) return 'just now'
        if (secs < 3600) return `${Math.floor(secs / 60)} min ago`
        if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`
        return new Date(utc).toLocaleString()
    } catch {
        return ''
    }
}

export function truncate(s: string, max: number): string {
    return s.length > max ? s.slice(0, max) + '…' : s
}
