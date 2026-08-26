import { m, useReducedMotion } from 'motion/react'
import { Skeleton } from '@/components/ui/skeleton'

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
                    <div className="flex h-[260px] items-center justify-center">
                        <Skeleton className="h-40 w-40 rounded-full opacity-40" />
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

