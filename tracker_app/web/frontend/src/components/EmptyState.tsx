import { m } from 'motion/react'
import { Network } from 'lucide-react'
import { easeOut } from '@/lib/animation'

interface EmptyStateProps {
    label: string
    hint?: string
}

/** Terminal-styled empty state with a blinking cursor. */
export default function EmptyState({ label, hint }: EmptyStateProps) {
    return (
        <m.div
            className="flex h-48 flex-col items-center justify-center gap-3 text-muted-foreground"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, ease: easeOut }}
        >
            <Network size={36} strokeWidth={1} className="text-muted" />
            <p className="font-mono text-xs uppercase tracking-widest text-foreground/60">
                {label}
                <span className="text-primary animate-blink-cursor">_</span>
            </p>
            {hint && <p className="max-w-xs text-center font-mono text-[11px] text-muted-foreground">{hint}</p>}
        </m.div>
    )
}
