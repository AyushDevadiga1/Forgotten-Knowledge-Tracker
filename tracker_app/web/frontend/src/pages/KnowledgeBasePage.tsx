import { useEffect, useState, useMemo } from 'react'
import { Database, Search } from 'lucide-react'
import { m, useReducedMotion } from 'motion/react'
import { api, LearningItem } from '../api'
import PageHeader from '../components/PageHeader'
import EmptyState from '../components/EmptyState'
import { Skeleton } from '../components/ui/skeleton'
import { easeOut } from '../lib/animation'
import { cn } from '@/lib/utils'

const diffColor: Record<string, string> = {
    easy: 'text-primary',
    medium: 'text-[#F59E0B]',
    hard: 'text-[#EF4444]',
}

export default function KnowledgeBasePage() {
    const [items, setItems] = useState<LearningItem[]>([])
    const [query, setQuery] = useState('')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const reduced = useReducedMotion()

    useEffect(() => {
        api.getItems('all', 200)
            .then((res) => setItems(res.data))
            .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
            .finally(() => setLoading(false))
    }, [])

    const filtered = useMemo(() => {
        const q = query.toLowerCase()
        if (q.length < 2) return items
        return items.filter(
            (i) =>
                i.question.toLowerCase().includes(q) ||
                i.item_type.toLowerCase().includes(q) ||
                (i.tags ?? []).join(' ').toLowerCase().includes(q)
        )
    }, [query, items])

    if (loading) {
        return (
            <div className="flex h-full flex-col gap-4">
                <Skeleton className="h-3 w-48" />
                <div className="flex-1 border border-border bg-card p-4">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <Skeleton key={i} className="mb-4 h-8 w-full" />
                    ))}
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex h-full items-center justify-center gap-3 font-mono text-xs text-[#EF4444]">
                Backend offline — {error}
            </div>
        )
    }

    return (
        <div className="flex h-full flex-col gap-4">
            <PageHeader icon={Database} title="Knowledge Base" subtitle="Every concept you have tracked and rated">
                <div className="flex items-center gap-3">
                    <span className="border border-border px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                        {filtered.length} ITEMS
                    </span>
                    <div className="flex w-64 items-center border border-border bg-card px-3 py-1.5 transition-colors focus-within:border-primary">
                        <Search size={13} strokeWidth={1.5} className="mr-2 shrink-0 text-muted-foreground" />
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Search questions, tags…"
                            className="w-full bg-transparent font-mono text-[12px] text-foreground outline-none placeholder:text-muted-foreground"
                        />
                    </div>
                </div>
            </PageHeader>

            <div className="flex-1 overflow-auto">
                {filtered.length === 0 ? (
                    <EmptyState
                        label={items.length === 0 ? 'No concepts yet — add some' : 'No matches found'}
                        hint={items.length === 0 ? 'Use Add to ingest your first concept.' : 'Try a different search term.'}
                    />
                ) : (
                    <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3">
                        {filtered.map((item, i) => (
                            <m.div
                                key={item.id}
                                initial={reduced ? false : { opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: Math.min(i * 0.02, 0.3), duration: 0.25, ease: easeOut }}
                                className="border border-border bg-background p-4 transition-colors hover:border-primary/30 hover:shadow-fkt-glow-sm"
                            >
                                <div className="mb-2 flex items-start justify-between gap-2">
                                    <span className="line-clamp-2 text-sm text-foreground">{item.question}</span>
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                    <span className="border border-border px-1.5 py-0.5 font-mono text-[9px] uppercase text-muted-foreground">{item.item_type}</span>
                                    <span className={cn('font-mono text-[9px] uppercase', diffColor[item.difficulty] ?? 'text-muted-foreground')}>{item.difficulty}</span>
                                    <span className="font-mono text-[10px] text-primary">{Math.round(item.success_rate)}%</span>
                                    <span className="font-mono text-[10px] text-muted-foreground">{item.total_reviews} reviews</span>
                                </div>
                                {item.next_review_date && (
                                    <p className="mt-2 font-mono text-[9px] text-muted-foreground">
                                        next: {new Date(item.next_review_date).toLocaleDateString()}
                                    </p>
                                )}
                            </m.div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}