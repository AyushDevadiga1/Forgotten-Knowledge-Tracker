import { useEffect, useState } from 'react'
import { m, AnimatePresence, useReducedMotion } from 'motion/react'
import { X, Check, ThumbsDown } from 'lucide-react'
import { api, IntentPrediction } from '../api'
import { spring } from '@/lib/animation'

function formatAgo(iso: string): string {
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

function truncate(s: string, max: number): string {
    return s.length > max ? s.slice(0, max) + '…' : s
}

// Dismissal is persisted per prediction (L-4). The backend also stamps
// prompted_at on first serve, so a dismissed prediction never resurfaces even
// after the toast unmounts (navigation) or the page reloads.
const DISMISS_PREFIX = 'fkt:dismissed-intent:'

function isDismissed(id: number): boolean {
    try {
        return localStorage.getItem(DISMISS_PREFIX + id) === '1'
    } catch {
        return false
    }
}

function markDismissed(id: number): void {
    try {
        localStorage.setItem(DISMISS_PREFIX + id, '1')
    } catch {
        // storage unavailable — the backend prompted_at claim still prevents re-show
    }
}

export default function IntentFeedbackToast() {
    const [prediction, setPrediction] = useState<IntentPrediction | null>(null)
    const [submitted, setSubmitted] = useState(false)
    const [actualIntent, setActualIntent] = useState('')
    const reduced = useReducedMotion()

    useEffect(() => {
        // Poll every 10 seconds for the latest prediction
        const checkRecent = async () => {
            try {
                const res = await api.getRecentIntent()
                const data = res.data
                // Only prompt if it exists and hasn't been given feedback yet.
                // The backend rate-limits (prompted_at + cooldown) so we only
                // get something worth showing here.
                if (data && data.user_feedback === null && !isDismissed(data.id)) {
                    setPrediction(data)
                    setSubmitted(false)
                    setActualIntent('')
                } else {
                    setPrediction(null)
                }
            } catch (e) {
                console.error('Failed to fetch recent intent', e)
            }
        }

        checkRecent()
        const interval = setInterval(checkRecent, 10000)
        return () => clearInterval(interval)
    }, [submitted]) // Re-run if submitted changes, though interval handles it

    const handleFeedback = async (isCorrect: boolean) => {
        if (!prediction) return
        try {
            await api.sendIntentFeedback(prediction.id, isCorrect, !isCorrect && actualIntent ? actualIntent : undefined)
            setSubmitted(true)
            // Hide immediately
            setPrediction(null)
        } catch (e) {
            console.error('Failed to submit feedback', e)
        }
    }

    const dismiss = () => {
        if (prediction) markDismissed(prediction.id)
        setPrediction(null)
    }

    return (
        <AnimatePresence>
            {prediction && (
                <m.div
                    key={prediction.id}
                    className="fixed bottom-6 right-6 z-50 w-80 border border-border bg-card shadow-2xl"
                    initial={reduced ? false : { x: 32, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={reduced ? undefined : { x: 32, opacity: 0 }}
                    transition={spring}
                >
                    <div className="flex items-center justify-between border-b border-border bg-background p-3">
                        <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                            <span className="h-1.5 w-1.5 animate-pulse bg-primary" />
                            Quick Check
                        </span>
                        <div className="flex items-center gap-3">
                            <span className="font-mono text-[9px] text-muted-foreground">
                                {Math.round(prediction.confidence * 100)}% CONF
                            </span>
                            <button
                                onClick={dismiss}
                                title="Dismiss"
                                aria-label="Dismiss"
                                className="leading-none text-muted-foreground transition-colors hover:text-foreground"
                            >
                                <X size={14} />
                            </button>
                        </div>
                    </div>

                    <div className="p-4">
                        <p className="mb-1 font-sans text-xs text-muted-foreground">
                            The system predicted your recent activity as:
                        </p>
                        <div className="mb-3 text-center font-mono text-lg uppercase text-primary drop-shadow-[0_0_10px_rgba(0,255,163,0.35)]">
                            {prediction.predicted_intent}
                        </div>

                        {(prediction.timestamp || prediction.window_title) && (
                            <div className="mb-3 flex items-center justify-center gap-2 font-mono text-[10px] text-muted-foreground">
                                {prediction.timestamp && <span>{formatAgo(prediction.timestamp)}</span>}
                                {prediction.timestamp && prediction.window_title && <span>•</span>}
                                {prediction.window_title && (
                                    <span className="max-w-[200px] truncate" title={prediction.window_title}>
                                        {truncate(prediction.window_title, 42)}
                                    </span>
                                )}
                            </div>
                        )}

                        <p className="mb-2 text-[10px] uppercase tracking-wide text-muted-foreground">Was this correct?</p>
                        <div className="mb-3 flex gap-2">
                            <m.button
                                onClick={() => handleFeedback(true)}
                                whileHover={reduced ? undefined : { scale: 1.02 }}
                                whileTap={reduced ? undefined : { scale: 0.97 }}
                                transition={{ duration: 0.12 }}
                                className="flex flex-1 items-center justify-center gap-1.5 border border-border bg-background py-2 font-mono text-xs text-foreground transition-colors hover:border-primary hover:text-primary"
                            >
                                <Check size={12} />
                                YES
                            </m.button>
                            <m.button
                                onClick={() => handleFeedback(false)}
                                whileHover={reduced ? undefined : { scale: 1.02 }}
                                whileTap={reduced ? undefined : { scale: 0.97 }}
                                transition={{ duration: 0.12 }}
                                className="flex flex-1 items-center justify-center gap-1.5 border border-border bg-background py-2 font-mono text-xs text-foreground transition-colors hover:border-[#EF4444] hover:text-[#EF4444]"
                            >
                                <ThumbsDown size={12} />
                                NO
                            </m.button>
                        </div>

                        {/* Optional correction field to improve data */}
                        <div className="mt-2 border-t border-border/60 pt-2">
                            <input
                                type="text"
                                placeholder="If no, what were you doing?"
                                value={actualIntent}
                                onChange={(e) => setActualIntent(e.target.value)}
                                className="w-full border border-border bg-transparent p-2 font-mono text-[11px] text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-[#F59E0B]"
                            />
                        </div>
                    </div>
                </m.div>
            )}
        </AnimatePresence>
    )
}
