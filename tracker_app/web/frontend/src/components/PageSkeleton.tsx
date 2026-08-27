import { m, useReducedMotion } from 'motion/react'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

function SkeletonCard({ delay = '0ms' }: { delay?: string }) {
    const reduced = useReducedMotion()
    return (
        <m.div
            className="border border-border bg-card p-4"
            style={{ animationDelay: delay }}
            initial={reduced ? false : { opacity: 0.6 }}
            animate={reduced ? {} : { opacity: [0.6, 1, 0.6] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
        >
            <Skeleton className="mb-4 h-2.5 w-24" />
            <Skeleton className="h-8 w-16" />
        </m.div>
    )
}

/** Overview page skeleton — mirrors the KPI + chart grid that is about to load. */
export function OverviewSkeleton() {
    return (
        <div className="space-y-3">
            <div className="grid grid-cols-4 gap-3">
                {Array.from({ length: 4 }).map((_, i) => (
                    <SkeletonCard key={i} delay={`${i * 60}ms`} />
                ))}
            </div>
            <div className="grid grid-cols-4 gap-3">
                <div className="col-span-2 border border-border bg-card p-4">
                    <Skeleton className="mb-4 h-2.5 w-40" />
                    <Skeleton className="h-[200px] w-full" />
                </div>
                <div className="col-span-1 border border-border bg-card p-4">
                    <Skeleton className="mb-4 h-2.5 w-24" />
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="mb-3 h-4 w-full" />
                    ))}
                </div>
                <div className="col-span-1 border border-border bg-card p-4">
                    <Skeleton className="mb-4 h-2.5 w-24" />
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="mb-3 h-5 w-full" />
                    ))}
                </div>
            </div>
        </div>
    )
}

/** Graph page skeleton — stat cards + a large graph-shaped block + gap list. */
export function GraphSkeleton() {
    return (
        <div className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
                {Array.from({ length: 3 }).map((_, i) => (
                    <SkeletonCard key={i} delay={`${i * 60}ms`} />
                ))}
            </div>
            <div className="grid grid-cols-5 gap-3">
                <div className="col-span-3 border border-border bg-card p-4">
                    <Skeleton className="mb-3 h-2.5 w-32" />
                    <div className="relative h-[260px]">
                        {[
                            { size: 'h-16 w-16', left: '12%', top: '20%', delay: '0ms' },
                            { size: 'h-11 w-11', left: '40%', top: '10%', delay: '120ms' },
                            { size: 'h-7 w-7', left: '70%', top: '25%', delay: '240ms' },
                            { size: 'h-12 w-12', left: '18%', top: '60%', delay: '90ms' },
                            { size: 'h-8 w-8', left: '55%', top: '70%', delay: '300ms' },
                        ].map((n, i) => (
                            <m.div
                                key={i}
                                className={cn('absolute rounded-full bg-slate-800', n.size)}
                                style={{ left: n.left, top: n.top, animationDelay: n.delay }}
                                initial={{ opacity: 0.25 }}
                                animate={{ opacity: [0.25, 0.6, 0.25] }}
                                transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                            />
                        ))}
                    </div>
                </div>
                <div className="col-span-2 border border-border bg-card p-4">
                    <Skeleton className="mb-4 h-2.5 w-24" />
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="mb-3 h-8 w-full" />
                    ))}
                </div>
            </div>
        </div>
    )
}

/** Quiz page skeleton — a card-shaped block. */
export function QuizSkeleton() {
    return (
        <div className="mx-auto max-w-xl space-y-4">
            <Skeleton className="h-4 w-40" />
            <div className="border border-border bg-card p-5">
                <Skeleton className="mb-6 h-4 w-3/4" />
                <div className="space-y-2">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="h-11 w-full" />
                    ))}
                </div>
            </div>
        </div>
    )
}
