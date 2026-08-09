import { m } from 'motion/react'
import { cn } from '@/lib/utils'

const config = {
    new: { label: 'New', cls: 'border-primary/40 bg-primary/10 text-primary', dot: 'bg-primary' },
    evolving: { label: 'Evolving', cls: 'border-amber-500/40 bg-amber-500/10 text-amber-500', dot: 'bg-amber-500' },
    stable: { label: 'Stable', cls: 'border-sky-400/40 bg-sky-400/10 text-sky-400', dot: 'bg-sky-400' },
    stagnant: { label: 'Stagnant', cls: 'border-red-500/40 bg-red-500/10 text-red-500', dot: 'bg-red-500' },
} as const

export type DriftStatus = keyof typeof config

interface DriftBadgeProps {
    status: DriftStatus
    className?: string
}

/** State-driven micro-badge for concept drift (new/evolving/stable/stagnant). */
export default function DriftBadge({ status, className }: DriftBadgeProps) {
    const c = config[status] ?? config.stable
    return (
        <m.span
            className={cn('inline-flex items-center gap-1.5 border px-2 py-0.5 text-[9px] font-mono uppercase tracking-widest', c.cls, className)}
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.2 }}
        >
            <m.span
                className={cn('h-1 w-1', c.dot)}
                animate={{ opacity: [0.35, 1, 0.35] }}
                transition={{ duration: 2, repeat: Infinity }}
            />
            {c.label}
        </m.span>
    )
}
