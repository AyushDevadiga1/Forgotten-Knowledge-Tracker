import { m } from 'motion/react'
import { cn } from '@/lib/utils'

const config = {
    easy: { label: 'Easy', cls: 'border-primary/40 bg-primary/10 text-primary', dot: 'bg-primary' },
    medium: { label: 'Medium', cls: 'border-amber-500/40 bg-amber-500/10 text-amber-500', dot: 'bg-amber-500' },
    hard: { label: 'Hard', cls: 'border-red-500/40 bg-red-500/10 text-red-500', dot: 'bg-red-500' },
} as const

interface DifficultyBadgeProps {
    difficulty?: string
    className?: string
}

/** Color-coded animated difficulty badge (easy/medium/hard). */
export default function DifficultyBadge({ difficulty, className }: DifficultyBadgeProps) {
    const c = config[(difficulty ?? '') as keyof typeof config] ?? config.medium
    return (
        <m.span
            className={cn('inline-flex items-center gap-1.5 border px-2 py-0.5 text-[9px] font-mono uppercase tracking-widest', c.cls, className)}
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            whileHover={{ scale: 1.05, boxShadow: '0 0 8px rgba(var(--primary-rgb), 0.2)' }}
        >
            <m.span
                className={cn('h-1 w-1', c.dot)}
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 2, repeat: Infinity }}
            />
            {c.label}
        </m.span>
    )
}
