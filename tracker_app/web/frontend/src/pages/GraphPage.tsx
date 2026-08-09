import { useEffect, useState, useCallback } from 'react'
import { Share2, RefreshCw, Network, AlertTriangle, MousePointer2 } from 'lucide-react'
import { m } from 'motion/react'
import { api, GraphStats, KnowledgeGap, ConceptDrift, GraphNode } from '@/api'
import PageHeader from '@/components/PageHeader'
import ForceGraph from '@/components/ForceGraph'
import ConceptPanel from '@/components/ConceptPanel'
import { GraphSkeleton } from '@/components/PageSkeleton'
import BackendDown from '@/components/BackendDown'
import DriftBadge, { type DriftStatus } from '@/components/DriftBadge'
import { cn } from '@/lib/utils'

function StatChip({ label, value, icon: Icon }: { label: string; value: string | number; icon: typeof Network }) {
    return (
        <div className="border border-border bg-card p-3.5">
            <div className="mb-2 flex items-center gap-1.5">
                <Icon size={11} strokeWidth={1.5} className="text-muted-foreground" />
                <span className="text-[9px] font-mono uppercase tracking-widest text-muted-foreground">{label}</span>
            </div>
            <span className="font-mono text-xl text-foreground">{value}</span>
        </div>
    )
}

function MemBar({ v, max = 1 }: { v: number; max?: number }) {
    const pct = Math.min(100, (v / max) * 100)
    const colour = pct > 65 ? 'bg-primary' : pct > 35 ? 'bg-[#F59E0B]' : 'bg-[#EF4444]'
    return (
        <div className="h-1 w-full overflow-hidden bg-slate-800">
            <m.div className={cn('h-full', colour)} initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.5 }} />
        </div>
    )
}

const LEGEND = [
    { color: '#00FFA3', label: 'strong ≥65' },
    { color: '#F59E0B', label: 'mid 40–64' },
    { color: '#EF4444', label: 'weak <40' },
]

export default function GraphPage() {
    const [stats, setStats] = useState<GraphStats | null>(null)
    const [gaps, setGaps] = useState<KnowledgeGap[]>([])
    const [drifts, setDrifts] = useState<Record<string, ConceptDrift>>({})
    const [selected, setSelected] = useState<GraphNode | null>(null)
    const [loading, setLoading] = useState(true)
    const [backendDown, setBackendDown] = useState(false)
    const [refreshing, setRefreshing] = useState(false)

    const load = useCallback(async (isRefresh = false) => {
        if (isRefresh) setRefreshing(true)
        try {
            const [statsRes, gapsRes] = await Promise.all([
                api.getGraphStats(),
                api.getKnowledgeGaps(8),
            ])
            setStats(statsRes.data)
            setGaps(gapsRes.data ?? [])
            const top = (statsRes.data.top_concepts ?? []).slice(0, 3)
            const driftRes = await Promise.allSettled(top.map((c) => api.getConceptDrift(c)))
            const map: Record<string, ConceptDrift> = {}
            driftRes.forEach((r, i) => {
                if (r.status === 'fulfilled' && top[i]) map[top[i]] = r.value.data
            })
            setDrifts(map)
            setBackendDown(false)
        } catch {
            setBackendDown(true)
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }, [])

    useEffect(() => { load() }, [load])

    if (loading) return <GraphSkeleton />
    if (backendDown) return <BackendDown />

    const nodes = stats?.nodes ?? []
    const links = stats?.edges ?? []

    return (
        <div className="space-y-4">
            <PageHeader
                icon={Share2}
                title="Knowledge Graph"
                subtitle="Concept network built from your tracked sessions"
            >
                <button
                    id="graph-refresh-btn"
                    onClick={() => load(true)}
                    disabled={refreshing}
                    className="flex items-center gap-1.5 border border-border px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                >
                    <RefreshCw size={11} className={refreshing ? 'animate-spin' : ''} />
                    Refresh
                </button>
            </PageHeader>

            <div className="grid grid-cols-3 gap-3">
                <StatChip label="Concepts" value={stats?.total_concepts ?? 0} icon={Network} />
                <StatChip label="Connections" value={stats?.total_edges ?? 0} icon={Share2} />
                <StatChip
                    label="Avg Memory"
                    value={stats ? `${(stats.avg_memory_strength * 100).toFixed(0)}%` : '—'}
                    icon={AlertTriangle}
                />
            </div>

            <div className="grid grid-cols-5 gap-3">
                {/* Visual graph */}
                <div className="col-span-3 border border-border bg-card p-4">
                    <div className="mb-3 flex items-center justify-between">
                        <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
                            Concept Map — top {nodes.length} nodes · force layout
                        </p>
                        <div className="flex items-center gap-3">
                            {LEGEND.map((l) => (
                                <span key={l.label} className="flex items-center gap-1.5 text-[9px] font-mono text-muted-foreground">
                                    <span className="h-1.5 w-1.5" style={{ background: l.color }} />
                                    {l.label}
                                </span>
                            ))}
                        </div>
                    </div>
                    <div className="flex gap-4">
                        <div className="flex-1">
                            {nodes.length === 0 ? (
                                <div className="flex h-[380px] flex-col items-center justify-center gap-3 text-muted-foreground">
                                    <Network size={32} strokeWidth={1} />
                                    <p className="text-[10px] font-mono uppercase tracking-widest">No concepts in graph yet</p>
                                    <p className="text-[10px] font-mono text-muted-foreground/70">Study in an active session to grow it.</p>
                                </div>
                            ) : (
                                <div className="h-[380px]">
                                    <ForceGraph nodes={nodes} links={links} onSelect={(n) => setSelected(n)} />
                                </div>
                            )}
                            <p className="mt-2 flex items-center gap-1.5 text-[9px] font-mono text-muted-foreground/70">
                                <MousePointer2 size={10} className="text-primary" />
                                click a node for memory + encounter history
                            </p>
                        </div>
                        <ConceptPanel
                            concept={selected?.concept ?? null}
                            memoryScore={selected?.memory_score ?? null}
                            onClose={() => setSelected(null)}
                        />
                    </div>
                </div>

                {/* Right rail: gaps + drift */}
                <div className="col-span-2 flex flex-col gap-3">
                    <div className="flex-1 border border-border bg-card p-4">
                        <p className="mb-3 flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
                            <AlertTriangle size={10} className="text-[#F59E0B]" />
                            Knowledge Gaps
                        </p>
                        {gaps.length === 0 ? (
                            <div className="flex h-32 items-center justify-center text-[10px] font-mono uppercase tracking-widest text-muted-foreground/70">
                                No gaps detected yet
                            </div>
                        ) : (
                            <ul className="space-y-3">
                                {gaps.map((g) => (
                                    <li key={g.concept}>
                                        <div className="mb-1 flex items-baseline justify-between">
                                            <span className="max-w-[150px] truncate font-mono text-xs text-foreground">{g.concept}</span>
                                            <span className="ml-2 shrink-0 font-mono text-[10px] text-muted-foreground">
                                                {(g.memory_strength * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <MemBar v={g.memory_strength} />
                                        <p className="mt-0.5 font-mono text-[9px] text-muted-foreground">
                                            last seen: {g.last_seen ? new Date(g.last_seen).toLocaleDateString() : 'never'}
                                        </p>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    {Object.keys(drifts).length > 0 && (
                        <div className="border border-border bg-card p-4">
                            <p className="mb-3 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
                                Concept Drift
                            </p>
                            <ul className="space-y-2">
                                {Object.entries(drifts).map(([concept, d]) => (
                                    <li key={concept} className="flex items-center justify-between">
                                        <span className="max-w-[140px] truncate font-mono text-[11px] text-foreground">{concept}</span>
                                        <DriftBadge status={d.status as DriftStatus} />
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
