import { m, useReducedMotion } from 'motion/react'
import { type LucideIcon } from 'lucide-react'
import AnimatedNumber from './AnimatedNumber'
import TrendChart from './TrendChart'
import { easeOut } from '@/lib/animation'
import { cn } from '@/lib/utils'

interface StatCardProps {
    title: string
    value: number
    format?: (v: number) => string
    delta?: string
    up?: boolean
    spark?: { v: number }[]
    sparkColor?: string
    icon?: LucideIcon
    delay?: number
    className?: string
}

/** Bklit-style KPI card: tiny mono label, animated counter, delta chip and a
 * real-data sparkline. Staggers in with the rest of the dashboard. */
export default function StatCard({
    title,
    value,
    format,
    delta,
    up,
    spark,
    sparkColor,
    icon: Icon,
    delay = 0,
    className,
}: StatCardProps) {
    const reduced = useReducedMotion()
    return (
        <m.div
            className={cn(
                'group relative flex flex-col justify-between border border-border bg-card p-4',
                'transition-colors duration-200 hover:border-primary/30 hover:shadow-fkt-glow-sm',
                className
            )}
            initial={reduced ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay, duration: 0.35, ease: easeOut }}
        >
            <div className="mb-4 flex items-start justify-between">
                <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">{title}</span>
                {delta && (
                    <span
                        className={cn(
                            'shrink-0 px-1.5 py-0.5 text-[10px] font-mono',
                            up === false ? 'bg-amber-500/10 text-amber-500' : 'bg-primary/10 text-primary'
                        )}
                    >
                        {delta}
                    </span>
                )}
            </div>
            <div className="flex items-end justify-between gap-3">
                <div className="flex min-w-0 flex-col gap-1.5">
                    {Icon && <Icon size={12} strokeWidth={1.5} className="text-muted-foreground" />}
                    <AnimatedNumber
                        value={value}
                        format={format}
                        className="font-mono text-3xl leading-none text-foreground"
                    />
                </div>
                {spark && spark.length > 1 && (
                    <div className="w-[80px] shrink-0">
                        <TrendChart data={spark} color={sparkColor ?? 'var(--primary)'} height={32} />
                    </div>
                )}
            </div>
        </m.div>
    )
}
