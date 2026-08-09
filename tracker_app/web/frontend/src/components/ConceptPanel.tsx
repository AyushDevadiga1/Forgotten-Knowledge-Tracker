import { useEffect, useState } from 'react'
import { m, AnimatePresence, useReducedMotion } from 'motion/react'
import { X, Activity, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { api, ConceptDetail, ConceptHistoryEntry } from '@/api'
import { cn } from '@/lib/utils'
import { easeOut } from '@/lib/animation'

function HistoryBar({ entry }: { entry: ConceptHistoryEntry }) {
    const pct = Math.max(8, Math.round((entry.confidence ?? 0.5) * 100))
    const color = (entry.confidence ?? 0) >= 0.65 ? 'bg-[#00FFA3]' : (entry.confidence ?? 0) >= 0.4 ? 'bg-[#F59E0B]' : 'bg-[#EF4444]'
    const when = entry.timestamp ? new Date(entry.timestamp) : null
    return (
        <li className="space-y-1">
            <div className="flex items-baseline justify-between">
                <span className="text-[10px] font-mono text-slate-400 truncate max-w-[70%]">
                    {entry.context ?? '—'}
                </span>
                <span className="text-[9px] font-mono text-slate-600 shrink-0">
                    {when ? when.toLocaleDateString() : '—'}
                </span>
            </div>
            <div className="h-1 w-full bg-slate-800/80">
                <m.div
                    className={cn('h-full', color)}
                    initial={false}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.5, ease: easeOut }}
                />
            </div>
        </li>
    )
}

interface ConceptPanelProps {
    concept: string | null
    memoryScore: number | null
    onClose: () => void
}

/** Right-hand drill-in panel: memory score + encounter history for one node. */
export default function ConceptPanel({ concept, memoryScore, onClose }: ConceptPanelProps) {
    const reduced = useReducedMotion()
    const [detail, setDetail] = useState<ConceptDetail | null>(null)
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (!concept) {
            setDetail(null)
            return
        }
        let alive = true
        setLoading(true)
        api.getConceptDetail(concept)
            .then((res) => alive && setDetail(res.data))
            .catch(() => alive && setDetail(null))
            .finally(() => alive && setLoading(false))
        return () => { alive = false }
    }, [concept])

    const hist = detail?.history ?? []
    const trend =
        hist.length >= 2
            ? (hist[hist.length - 1].confidence ?? 0) - (hist[0].confidence ?? 0)
            : 0
    const score = detail?.memory_score ?? memoryScore ?? 0
    const scorePct = Math.round(score * 100)
    const color = score >= 0.65 ? 'text-[#00FFA3]' : score >= 0.4 ? 'text-[#F59E0B]' : 'text-[#EF4444]'

    return (
        <AnimatePresence>
            {concept && (
                <m.aside
                    key="concept-panel"
                    initial={reduced ? false : { x: 24, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={reduced ? undefined : { x: 24, opacity: 0 }}
                    transition={{ duration: 0.22, ease: easeOut }}
                    className="flex flex-col bg-[#0A0F14] border-l border-slate-800 min-w-[280px] max-w-[300px]"
                >
                    <div className="flex items-center justify-between px-4 pt-4 pb-3 border-b border-slate-800/80">
                        <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500">Node Detail</p>
                        <button
                            onClick={onClose}
                            aria-label="Close panel"
                            className="text-slate-500 hover:text-[#00FFA3] transition-colors"
                        >
                            <X size={14} />
                        </button>
                    </div>

                    <div className="px-4 py-3 border-b border-slate-800/80">
                        <p className="text-sm font-mono text-slate-100 break-words leading-snug">{concept}</p>
                        <div className="mt-3 flex items-baseline gap-2">
                            <span className={cn('text-2xl font-mono', color)}>{scorePct}</span>
                            <span className="text-[10px] font-mono text-slate-500 uppercase">memory</span>
                        </div>
                        <div className="mt-1.5 h-1 w-full bg-slate-800/80">
                            <m.div
                                initial={reduced ? false : { width: 0 }}
                                animate={{ width: `${scorePct}%` }}
                                transition={{ duration: 0.6, ease: easeOut }}
                                className={cn('h-full', score >= 0.65 ? 'bg-[#00FFA3]' : score >= 0.4 ? 'bg-[#F59E0B]' : 'bg-[#EF4444]')}
                            />
                        </div>
                        {hist.length >= 2 && (
                            <p className="mt-2 flex items-center gap-1 text-[9px] font-mono text-slate-500">
                                {trend >= 0
                                    ? <ArrowUpRight size={10} className="text-[#00FFA3]" />
                                    : <ArrowDownRight size={10} className="text-[#EF4444]" />}
                                confidence {(trend >= 0 ? '+' : '') + trend.toFixed(2)} over {hist.length} encounters
                            </p>
                        )}
                    </div>

                    <div className="px-4 py-3 flex-1 overflow-y-auto">
                        <p className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-3">
                            <Activity size={10} className="text-[#00FFA3]" />
                            Encounter History
                        </p>
                        {loading ? (
                            <p className="text-[10px] font-mono text-slate-600">reading history…</p>
                        ) : hist.length === 0 ? (
                            <p className="text-[10px] font-mono text-slate-600">no encounters logged yet</p>
                        ) : (
                            <ul className="space-y-3">
                                {hist.slice(-8).reverse().map((h, i) => <HistoryBar key={i} entry={h} />)}
                            </ul>
                        )}
                    </div>
                </m.aside>
            )}
        </AnimatePresence>
    )
}
