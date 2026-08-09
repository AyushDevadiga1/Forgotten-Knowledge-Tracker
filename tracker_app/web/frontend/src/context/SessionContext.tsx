import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { api, SessionStatus } from '../api'

interface SessionContextValue {
    /** True while a study session is active (the tracker is capturing). */
    active: boolean
    status: SessionStatus | null
    busy: boolean
    toggle: () => Promise<void>
}

const SessionContext = createContext<SessionContextValue | undefined>(undefined)

/** Polls /session/status and exposes a shared toggle so the shell header and
 * the Overview page never disagree about whether FKT is capturing right now. */
export function SessionProvider({ children }: { children: ReactNode }) {
    const [status, setStatus] = useState<SessionStatus | null>(null)
    const [busy, setBusy] = useState(false)

    const refresh = useCallback(async () => {
        try {
            const res = await api.getSessionStatus()
            setStatus(res.data)
        } catch {
            /* backend offline — keep last known state */
        }
    }, [])

    useEffect(() => {
        refresh()
        const t = setInterval(refresh, 5000)
        return () => clearInterval(t)
    }, [refresh])

    const toggle = useCallback(async () => {
        if (busy) return
        setBusy(true)
        try {
            const res = status?.active ? await api.stopSession() : await api.startSession()
            setStatus(res.data)
        } catch {
            /* surface failure by refreshing last known state */
            await refresh()
        } finally {
            setBusy(false)
        }
    }, [busy, status?.active, refresh])

    return (
        <SessionContext.Provider value={{ active: status?.active ?? false, status, busy, toggle }}>
            {children}
        </SessionContext.Provider>
    )
}

export function useSession() {
    const ctx = useContext(SessionContext)
    if (!ctx) throw new Error('useSession must be used within SessionProvider')
    return ctx
}
