import { useEffect, useState } from 'react'
import { Search, Loader, AlertCircle } from 'lucide-react'
import { api, LearningItem } from '../api'

export default function KnowledgeBasePage() {
    const [items, setItems] = useState<LearningItem[]>([])
    const [filtered, setFiltered] = useState<LearningItem[]>([])
    const [query, setQuery] = useState('')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        api.getItems('all', 200)
            .then(res => { setItems(res.data); setFiltered(res.data) })
            .catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
            .finally(() => setLoading(false))
    }, [])

    useEffect(() => {
        const q = query.toLowerCase()
        setFiltered(
            q.length < 2
                ? items
                : items.filter(i =>
                    i.question.toLowerCase().includes(q) ||
                    i.item_type.toLowerCase().includes(q) ||
                    (i.tags ?? '').toLowerCase().includes(q)
                )
        )
    }, [query, items])

    const diffColor: Record<string, string> = {
        easy: 'text-fkt-accent',
        medium: 'text-[#F59E0B]',
        hard: 'text-[#EF4444]',
    }

    if (loading) return (
        <div className="flex items-center justify-center h-full gap-3 text-fkt-text-muted">
            <Loader size={18} strokeWidth={1.5} className="animate-spin text-fkt-accent" />
            <span className="font-mono text-xs uppercase tracking-widest">Loading knowledge base…</span>
        </div>
    )

    if (error) return (
        <div className="flex items-center justify-center h-full gap-3 text-[#EF4444]">
            <AlertCircle size={18} strokeWidth={1.5} />
            <span className="font-mono text-xs">Backend offline — {error}</span>
        </div>
    )

    return (
        <div className="flex flex-col h-full gap-4">

            {/* Header */}
            <div className="flex justify-between items-center shrink-0">
                <div className="flex items-center gap-4">
                    <h1 className="font-mono text-fkt-text-primary text-sm uppercase tracking-widest">Knowledge Base</h1>
                    <span className="font-mono text-[10px] text-fkt-text-muted border border-fkt-elevated px-2 py-0.5">{filtered.length} ITEMS</span>
                </div>
                <div className="flex items-center border border-fkt-elevated bg-fkt-surface px-3 py-1.5 w-64 focus-within:border-fkt-accent transition-colors">
                    <Search size={13} className="text-fkt-text-muted mr-2 shrink-0" strokeWidth={1.5} />
                    <input
                        type="text"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        placeholder="Search questions, tags…"
                        className="bg-transparent border-none outline-none text-[12px] font-mono text-fkt-text-primary w-full placeholder:text-fkt-text-dim"
                    />
                </div>
            </div>

            {/* Table */}
            <div className="bg-fkt-surface border border-fkt-elevated flex-1 overflow-auto">
                {filtered.length === 0 ? (
                    <div className="flex items-center justify-center h-full">
                        <span className="font-mono text-fkt-text-dim text-xs uppercase tracking-widest">
                            {items.length === 0 ? 'No concepts yet — add some!' : 'No matches found'}
                        </span>
                    </div>
                ) : (
                    <table className="w-full text-left">
                        <thead className="bg-fkt-base border-b border-fkt-elevated sticky top-0">
                            <tr>
                                {['Question', 'Type', 'Difficulty', 'Success', 'Reviews', 'Next Review'].map(h => (
                                    <th key={h} className="p-3 text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted font-normal whitespace-nowrap">{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map(item => (
                                <tr key={item.id} className="border-b border-fkt-elevated/40 hover:bg-fkt-elevated transition-colors cursor-pointer group">
                                    <td className="p-3 text-fkt-text-primary text-sm max-w-[280px]">
                                        <span className="truncate block" title={item.question}>{item.question}</span>
                                    </td>
                                    <td className="p-3 font-mono text-[10px] text-fkt-text-muted uppercase">{item.item_type}</td>
                                    <td className={`p-3 font-mono text-[10px] uppercase ${diffColor[item.difficulty] ?? 'text-fkt-text-muted'}`}>{item.difficulty}</td>
                                    <td className="p-3 font-mono text-[12px] text-fkt-accent">{Math.round(item.success_rate)}%</td>
                                    <td className="p-3 font-mono text-[12px] text-fkt-text-muted">{item.total_reviews}</td>
                                    <td className="p-3 font-mono text-[10px] text-fkt-text-dim">
                                        {item.next_review_date ? new Date(item.next_review_date).toLocaleDateString() : '—'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    )
}
