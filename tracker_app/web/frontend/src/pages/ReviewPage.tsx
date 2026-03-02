import { useEffect, useState, useCallback } from 'react'
import { ChevronRight, Loader, AlertCircle, CheckCircle } from 'lucide-react'
import { api, LearningItem } from '../api'

const QUALITY_LABELS = [
    { label: 'AGAIN', q: 0, desc: 'Complete blackout' },
    { label: 'HARD', q: 2, desc: 'Significant effort' },
    { label: 'GOOD', q: 4, desc: 'Correct with hesitation' },
    { label: 'EASY', q: 5, desc: 'Perfect recall' },
]

export default function ReviewPage() {
    const [dueItems, setDueItems] = useState<LearningItem[]>([])
    const [currentIdx, setCurrentIdx] = useState(0)
    const [revealed, setRevealed] = useState(false)
    const [loading, setLoading] = useState(true)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [done, setDone] = useState(false)

    const loadDue = useCallback(async () => {
        try {
            const res = await api.getDueItems()
            setDueItems(res.data)
            setCurrentIdx(0)
            setRevealed(false)
            setDone(res.data.length === 0)
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to load due items')
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { loadDue() }, [loadDue])

    const handleRate = async (quality: number) => {
        const item = dueItems[currentIdx]
        if (!item) return
        setSubmitting(true)
        try {
            await api.recordReview(item.id, quality)
            const nextIdx = currentIdx + 1
            if (nextIdx >= dueItems.length) {
                setDone(true)
            } else {
                setCurrentIdx(nextIdx)
                setRevealed(false)
            }
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to record review')
        } finally {
            setSubmitting(false)
        }
    }

    if (loading) return (
        <div className="flex items-center justify-center h-full gap-3 text-fkt-text-muted">
            <Loader size={18} strokeWidth={1.5} className="animate-spin text-fkt-accent" />
            <span className="font-mono text-xs uppercase tracking-widest">Loading due items…</span>
        </div>
    )

    if (error) return (
        <div className="flex items-center justify-center h-full gap-3 text-[#EF4444]">
            <AlertCircle size={18} strokeWidth={1.5} />
            <span className="font-mono text-xs">Error — {error}</span>
        </div>
    )

    if (done) return (
        <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
            <CheckCircle size={40} strokeWidth={1} className="text-fkt-accent" />
            <h2 className="text-fkt-text-primary font-sans text-xl">Review Complete</h2>
            <p className="text-fkt-text-muted font-mono text-xs max-w-xs">
                No items currently due for review. Well done — your memory is up to date.
            </p>
            <button
                onClick={() => { setLoading(true); setDone(false); loadDue() }}
                className="mt-4 px-6 py-3 border border-fkt-accent text-fkt-accent font-mono text-[11px] uppercase hover:bg-fkt-accent/10 transition-colors"
            >
                CHECK AGAIN
            </button>
        </div>
    )

    const item = dueItems[currentIdx]
    const progress = Math.round(((currentIdx) / dueItems.length) * 100)

    return (
        <div className="flex flex-col items-center justify-center h-full">
            <div className="w-full max-w-2xl">

                {/* Progress bar */}
                <div className="flex justify-between items-center mb-4 text-fkt-text-muted">
                    <span className="text-[10px] uppercase tracking-[0.12em] font-mono">
                        ITEM {currentIdx + 1} OF {dueItems.length} DUE
                    </span>
                    <span className="font-mono text-fkt-accent text-xs">{progress}% COMPLETE</span>
                </div>
                <div className="w-full h-[1px] bg-fkt-elevated mb-6">
                    <div className="h-full bg-fkt-accent transition-all duration-500" style={{ width: `${progress}%` }} />
                </div>

                {/* Card */}
                <div className="bg-fkt-surface border border-fkt-elevated p-8 min-h-[320px] flex flex-col hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow [clip-path:polygon(0_0,calc(100%-16px)_0,100%_16px,100%_100%,0_100%)]">
                    {/* Meta tags */}
                    <div className="flex gap-2 mb-6">
                        <span className="text-[9px] font-mono uppercase px-2 py-0.5 border border-fkt-elevated text-fkt-text-dim">{item.difficulty}</span>
                        <span className="text-[9px] font-mono uppercase px-2 py-0.5 border border-fkt-elevated text-fkt-text-dim">{item.item_type}</span>
                        {item.success_rate > 0 && (
                            <span className="text-[9px] font-mono uppercase px-2 py-0.5 border border-fkt-accent/30 text-fkt-accent">{Math.round(item.success_rate)}% SUCCESS</span>
                        )}
                    </div>

                    <h2 className="text-xl text-fkt-text-primary font-sans mb-auto">{item.question}</h2>

                    {/* Reveal / Answer */}
                    {!revealed ? (
                        <button
                            onClick={() => setRevealed(true)}
                            className="mt-8 flex items-center justify-center gap-2 w-full py-3 border border-fkt-elevated text-fkt-text-muted hover:border-fkt-accent hover:text-fkt-accent font-mono text-[11px] uppercase transition-colors"
                        >
                            REVEAL ANSWER <ChevronRight size={14} strokeWidth={1.5} />
                        </button>
                    ) : (
                        <>
                            <div className="mt-6 p-4 bg-fkt-base border border-fkt-elevated border-l-2 border-l-fkt-accent text-fkt-text-muted text-sm leading-relaxed">
                                {item.answer}
                            </div>
                            <div className="flex gap-[1px] mt-6 bg-fkt-elevated p-[1px]">
                                {QUALITY_LABELS.map(({ label, q, desc }) => (
                                    <button
                                        key={label}
                                        disabled={submitting}
                                        onClick={() => handleRate(q)}
                                        title={desc}
                                        className="flex-1 bg-fkt-surface py-3 text-[10px] font-mono text-fkt-text-muted hover:text-fkt-accent hover:bg-fkt-base transition-colors disabled:opacity-40 disabled:cursor-wait"
                                    >
                                        {submitting ? '…' : label}
                                    </button>
                                ))}
                            </div>
                        </>
                    )}
                </div>

            </div>
        </div>
    )
}
