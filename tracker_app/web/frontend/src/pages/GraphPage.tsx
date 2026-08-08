import { useEffect, useState, useCallback } from 'react'
import { Network, AlertTriangle, RefreshCw, Loader, TrendingDown, Cpu, Share2 } from 'lucide-react'
import { api, GraphStats, KnowledgeGap, GraphEdge } from '../api'

// ── tiny shared helpers ───────────────────────────────────
function MemBar({ v, max = 1 }: { v: number; max?: number }) {
    const pct = Math.min(100, (v / max) * 100)
    const colour =
        pct > 65 ? 'bg-fkt-accent' : pct > 35 ? 'bg-[#F59E0B]' : 'bg-[#EF4444]'
    return (
        <div className="h-1 w-full bg-fkt-elevated rounded-none overflow-hidden">
            <div className={`h-full ${colour} transition-all duration-500`} style={{ width: `${pct}%` }} />
        </div>
    )
}

function EmptyState({ label }: { label: string }) {
    return (
        <div className="flex flex-col items-center justify-center h-48 text-fkt-text-dim gap-3">
            <Network size={36} strokeWidth={1} />
            <p className="text-xs font-mono uppercase tracking-widest">{label}</p>
        </div>
    )
}

function BackendDown() {
    return (
        <div className="flex flex-col items-center justify-center h-64 gap-4 text-fkt-text-muted">
            <AlertTriangle size={40} strokeWidth={1} className="text-[#EF4444]" />
            <p className="text-sm font-mono">Backend offline — start <code className="text-fkt-accent">main.py</code> and <code className="text-fkt-accent">web/app.py</code></p>
            <p className="text-[11px] text-fkt-text-dim">Graph data will appear automatically once connected.</p>
        </div>
    )
}

// ── Force-layout mini graph rendered on an SVG canvas ────
function BubbleGraph({ concepts, edges }: { concepts: string[]; edges: GraphEdge[] }) {
    if (concepts.length === 0) return <EmptyState label="No concepts in graph yet" />

    const W = 480, H = 260, CX = W / 2, CY = H / 2
    // evenly place on an ellipse
    const nodes = concepts.slice(0, 20).map((c, i, arr) => {
        const angle = (2 * Math.PI * i) / arr.length - Math.PI / 2
        const rx = CX * 0.72, ry = CY * 0.72
        return { label: c, x: CX + rx * Math.cos(angle), y: CY + ry * Math.sin(angle) }
    })
    const pos = new Map(nodes.map(n => [n.label, n]))

    // Real semantic edges (M-7): draw only links that exist in the backend
    // graph, with stroke width/opacity scaled by weight — no fabricated HUB.
    const lines = edges.map((e, i) => {
        const a = pos.get(e.source), b = pos.get(e.target)
        if (!a || !b) return null
        return (
            <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke="#00FFA3" strokeWidth={0.6 + e.weight * 2}
                opacity={0.25 + e.weight * 0.6} />
        )
    })

    return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full">
            {lines}
            {/* concept nodes */}
            {nodes.map((n, i) => (
                <g key={i}>
                    <circle cx={n.x} cy={n.y} r={9} fill="#0F172A" stroke="#334155" strokeWidth={1} />
                    <text x={n.x} y={n.y - 13} textAnchor="middle" fontSize={8}
                        fill="#94A3B8" fontFamily="IBM Plex Mono"
                        className="pointer-events-none select-none">
                        {n.label.length > 12 ? n.label.slice(0, 11) + '…' : n.label}
                    </text>
                </g>
            ))}
            {edges.length === 0 && (
                <text x={CX} y={CY} textAnchor="middle" fontSize={9}
                    fill="#475569" fontFamily="IBM Plex Mono">
                    no semantic links among top concepts yet
                </text>
            )}
        </svg>
    )
}

// ── Main page ─────────────────────────────────────────────
export default function GraphPage() {
    const [stats, setStats] = useState<GraphStats | null>(null)
    const [gaps, setGaps] = useState<KnowledgeGap[]>([])
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
            setBackendDown(false)
        } catch {
            setBackendDown(true)
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }, [])

    useEffect(() => { load() }, [load])

    if (loading) return (
        <div className="flex items-center justify-center h-64 gap-3 text-fkt-text-muted">
            <Loader size={18} className="animate-spin" />
            <span className="text-xs font-mono">Loading knowledge graph…</span>
        </div>
    )

    if (backendDown) return <BackendDown />

    const topConcepts = stats?.top_concepts ?? []

    return (
        <div className="space-y-5">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-fkt-text-primary font-mono text-sm uppercase tracking-widest flex items-center gap-2">
                        <Share2 size={14} className="text-fkt-accent" />
                        Knowledge Graph
                    </h1>
                    <p className="text-[11px] text-fkt-text-dim mt-0.5 font-mono">
                        Concept network built from your tracked sessions
                    </p>
                </div>
                <button
                    id="graph-refresh-btn"
                    onClick={() => load(true)}
                    disabled={refreshing}
                    className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-widest text-fkt-text-muted
                               border border-fkt-elevated px-3 py-1.5 hover:border-fkt-accent hover:text-fkt-accent transition-colors"
                >
                    <RefreshCw size={11} className={refreshing ? 'animate-spin' : ''} />
                    Refresh
                </button>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-3">
                {[
                    { label: 'Concepts', value: stats?.total_concepts ?? 0, icon: Cpu },
                    { label: 'Connections', value: stats?.total_edges ?? 0, icon: Share2 },
                    { label: 'Avg Memory', value: stats ? `${(stats.avg_memory_strength * 100).toFixed(0)}%` : '—', icon: TrendingDown },
                ].map(({ label, value, icon: Icon }) => (
                    <div key={label} className="bg-fkt-surface border border-fkt-elevated p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <Icon size={12} strokeWidth={1.5} className="text-fkt-text-dim" />
                            <span className="text-[10px] font-mono uppercase tracking-widest text-fkt-text-dim">{label}</span>
                        </div>
                        <span className="text-2xl font-mono text-fkt-text-primary">{value}</span>
                    </div>
                ))}
            </div>

            {/* Graph + Gaps side by side */}
            <div className="grid grid-cols-5 gap-3">
                {/* Visual graph */}
                <div className="col-span-3 bg-fkt-surface border border-fkt-elevated p-4">
                    <p className="text-[10px] font-mono uppercase tracking-widest text-fkt-text-dim mb-3">
                        Concept Map — top {Math.min(20, topConcepts.length)} nodes
                    </p>
                    <div className="h-[260px]">
                        <BubbleGraph concepts={topConcepts} edges={stats?.edges ?? []} />
                    </div>
                </div>

                {/* Knowledge gaps */}
                <div className="col-span-2 bg-fkt-surface border border-fkt-elevated p-4 flex flex-col">
                    <p className="text-[10px] font-mono uppercase tracking-widest text-fkt-text-dim mb-3 flex items-center gap-2">
                        <AlertTriangle size={10} className="text-[#F59E0B]" />
                        Knowledge Gaps
                    </p>
                    {gaps.length === 0
                        ? <EmptyState label="No gaps detected yet" />
                        : (
                            <ul className="space-y-3 overflow-y-auto flex-1">
                                {gaps.map((g) => (
                                    <li key={g.concept} className="group">
                                        <div className="flex justify-between items-baseline mb-1">
                                            <span className="text-xs text-fkt-text-primary font-mono truncate max-w-[130px]">{g.concept}</span>
                                            <span className="text-[10px] text-fkt-text-dim font-mono shrink-0 ml-2">
                                                {(g.memory_strength * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <MemBar v={g.memory_strength} />
                                        <p className="text-[9px] text-fkt-text-dim mt-0.5 font-mono">
                                            Last seen: {g.last_seen ? new Date(g.last_seen).toLocaleDateString() : 'never'}
                                        </p>
                                    </li>
                                ))}
                            </ul>
                        )
                    }
                </div>
            </div>
        </div>
    )
}
