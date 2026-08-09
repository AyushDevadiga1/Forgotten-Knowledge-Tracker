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

            <div className="flex-1 overflow-auto border border-border bg-card">
                {filtered.length === 0 ? (
                    <EmptyState
                        label={items.length === 0 ? 'No concepts yet — add some' : 'No matches found'}
                        hint={items.length === 0 ? 'Use Add to ingest your first concept.' : 'Try a different search term.'}
                    />
                ) : (
                    <table className="w-full text-left">
                        <thead className="sticky top-0 border-b border-border bg-background">
                            <tr>
                                {['Question', 'Type', 'Difficulty', 'Success', 'Reviews', 'Next Review'].map((h) => (
                                    <th key={h} className="whitespace-nowrap p-3 text-[10px] font-normal uppercase tracking-[0.12em] text-muted-foreground">
                                        {h}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map((item, i) => (
                                <m.tr
                                    key={item.id}
                                    initial={reduced ? false : { opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ delay: Math.min(i * 0.015, 0.4), duration: 0.25, ease: easeOut }}
                                    className="group cursor-pointer border-b border-border/40 transition-colors hover:bg-slate-800/40"
                                >
                                    <td className="max-w-[280px] p-3 text-sm text-foreground">
                                        <span className="block truncate" title={item.question}>
                                            {item.question}
                                        </span>
                                    </td>
                                    <td className="p-3 font-mono text-[10px] uppercase text-muted-foreground">{item.item_type}</td>
                                    <td className={cn('p-3 font-mono text-[10px] uppercase', diffColor[item.difficulty] ?? 'text-muted-foreground')}>
                                        {item.difficulty}
                                    </td>
                                    <td className="p-3 font-mono text-[12px] text-primary">{Math.round(item.success_rate)}%</td>
                                    <td className="p-3 font-mono text-[12px] text-muted-foreground">{item.total_reviews}</td>
                                    <td className="p-3 font-mono text-[10px] text-muted-foreground">
                                        {item.next_review_date ? new Date(item.next_review_date).toLocaleDateString() : '—'}
                                    </td>
                                </m.tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    )
}
