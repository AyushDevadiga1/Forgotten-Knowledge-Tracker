import { useEffect, useState } from 'react'
import { m, useReducedMotion } from 'motion/react'
import { easeOut } from '@/lib/animation'

interface BackendDownProps {
    hint?: string
}

export default function BackendDown({ hint }: BackendDownProps) {
    const reduced = useReducedMotion()
    const message = hint ?? 'Data will appear automatically once connected.'
    const [displayed, setDisplayed] = useState(reduced ? message : '')

    useEffect(() => {
        if (reduced) return
        let i = 0
        const timer = setInterval(() => {
            i++
            setDisplayed(message.slice(0, i))
            if (i >= message.length) clearInterval(timer)
        }, 30)
        return () => clearInterval(timer)
    }, [message, reduced])

    return (
        <m.div
            className="flex h-64 flex-col items-center justify-center gap-4 text-muted-foreground"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, ease: easeOut }}
        >
            <div className="font-mono text-[11px] uppercase tracking-widest text-destructive/80">
                $ connection_lost
            </div>
            <p className="font-mono text-xs text-foreground/80">
                Backend offline — start <span className="text-primary">main.py</span> and{' '}
                <span className="text-primary">web/app.py</span>
            </p>
            <p className="font-mono text-[11px] text-muted-foreground">
                {displayed}
                <span className="text-primary animate-blink-cursor">_</span>
            </p>
        </m.div>
    )
}
