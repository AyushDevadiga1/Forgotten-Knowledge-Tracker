import { useEffect, useRef, useState, useCallback } from 'react'
import { m, useReducedMotion } from 'motion/react'
import { Play, Square, Loader2 } from 'lucide-react'
import { useSession } from '@/context/SessionContext'
import { api } from '@/api'
import { cn } from '@/lib/utils'
import { spring } from '@/lib/animation'
import { formatElapsed } from '@/lib/format'

interface SessionToggleButtonProps {
    size?: 'default' | 'sm'
    className?: string
}

/** The most important control in the app — Start/Stop Studying. When a
 * session is active it emits a slow ambient glow ("FKT is watching right now"
 * at a glance) and pulses, with a press-ripple on click. */
export default function SessionToggleButton({ size = 'default', className }: SessionToggleButtonProps) {
    const { active, busy, toggle, status } = useSession()
    const reduced = useReducedMotion()
    const [ripple, setRipple] = useState(false)
    const [calibrating, setCalibrating] = useState(false)
    const [calProgress, setCalProgress] = useState(0)
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const calTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

    useEffect(() => () => {
        if (timerRef.current) clearTimeout(timerRef.current)
        if (calTimerRef.current) clearInterval(calTimerRef.current)
    }, [])

    const runCalibration = useCallback(async () => {
        setCalibrating(true)
        setCalProgress(0)
        const duration = 30
        const step = 100 / (duration * 10)
        calTimerRef.current = setInterval(() => {
            setCalProgress(prev => {
                if (prev >= 100) {
                    if (calTimerRef.current) clearInterval(calTimerRef.current)
                    return 100
                }
                return prev + step
            })
        }, 100)
        try {
            await api.calibrateSession(duration)
        } catch {
            // calibration failed silently; defaults will be used
        } finally {
            if (calTimerRef.current) clearInterval(calTimerRef.current)
            setCalProgress(100)
            setTimeout(() => setCalibrating(false), 500)
        }
    }, [])

    const handleClick = async () => {
        if (busy) return
        setRipple(true)
        if (timerRef.current) clearTimeout(timerRef.current)
        timerRef.current = setTimeout(() => setRipple(false), 450)
        if (!active) {
            toggle()
            await runCalibration()
        } else {
            toggle()
        }
    }

    const sm = size === 'sm'
    return (
        <div className={cn('flex items-center gap-2.5', className)}>
            {calibrating && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 size={14} className="animate-spin" />
                    <span>Calibrating eyes ({Math.round(calProgress)}%)</span>
                    <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                            className="h-full bg-primary rounded-full transition-all duration-100"
                            style={{ width: `${calProgress}%` }}
                        />
                    </div>
                </div>
            )}
            {active && (
                <span className="font-mono text-primary tabular-nums" aria-live="off">
                    {formatElapsed(status?.elapsed_seconds)}
                </span>
            )}
            <m.button
                type="button"
                onClick={handleClick}
                disabled={busy}
                whileTap={reduced ? undefined : { scale: 0.94 }}
                aria-pressed={active}
                className={cn(
                    'relative isolate flex items-center gap-2 overflow-hidden border font-mono uppercase tracking-widest transition-colors disabled:cursor-wait disabled:opacity-60',
                    sm ? 'px-2.5 py-1.5 text-[9px]' : 'px-4 py-2 text-[10px]',
                    active
                        ? 'border-destructive/50 text-destructive hover:bg-destructive/10'
                        : 'border-primary/50 text-primary hover:bg-primary/10'
                )}
            >
                {/* ambient glow + pulse while a session is live */}
                {active && (
                    <m.span
                        className="pointer-events-none absolute inset-0 -z-10"
                        animate={reduced ? { opacity: 0.5 } : { opacity: [0.35, 0.9, 0.35], boxShadow: ['0 0 10px rgba(0,255,163,0.25)', '0 0 24px rgba(0,255,163,0.55)', '0 0 10px rgba(0,255,163,0.25)'] }}
                        transition={{ duration: 2.6, repeat: Infinity, ease: 'easeInOut' }}
                    />
                )}
                {/* press ripple */}
                {ripple && !reduced && (
                    <m.span
                        key={String(ripple)}
                        className="pointer-events-none absolute inset-0 -z-10 bg-primary/15"
                        initial={{ scale: 0.4, opacity: 1 }}
                        animate={{ scale: 1.6, opacity: 0 }}
                        transition={spring}
                    />
                )}
                {active ? <Square size={sm ? 11 : 14} strokeWidth={1.5} /> : <Play size={sm ? 11 : 14} strokeWidth={1.5} />}
                {active ? 'Stop Studying' : 'Start Studying'}
            </m.button>
        </div>
    )
}
