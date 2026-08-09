import { Flame } from 'lucide-react'
import { m, useReducedMotion } from 'motion/react'
import { cn } from '@/lib/utils'

interface StreakFlameProps {
    streak: number
    className?: string
}

/** Animated streak flame whose glow intensifies with streak length — gives the
 * existing streak number emotional weight without inventing a new metric. */
export default function StreakFlame({ streak, className }: StreakFlameProps) {
    const reduced = useReducedMotion()
    const intensity = Math.min(1, Math.max(0, streak) / 21)
    const lit = streak > 0
    const glow = lit
        ? `0 0 ${6 + intensity * 16}px rgba(0,255,163,${0.25 + intensity * 0.45})`
        : 'none'

    return (
        <div className={cn('relative inline-flex items-center justify-center', className)} title={`${streak} day streak`}>
            {lit && (
                <m.div
                    className="absolute -inset-2 rounded-full"
                    animate={
                        reduced
                            ? { opacity: 0.5 }
                            : { scale: [1, 1.22, 1], opacity: [0.35, 0.75, 0.35] }
                    }
                    transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
                    style={{ boxShadow: glow, background: 'rgba(0,255,163,0.05)' }}
                />
            )}
            <Flame
                size={20}
                strokeWidth={1.5}
                fill={lit ? `rgba(0,255,163,${0.18 + intensity * 0.4})` : 'none'}
                className={cn('relative transition-colors', lit ? 'text-primary' : 'text-muted-foreground')}
            />
        </div>
    )
}
