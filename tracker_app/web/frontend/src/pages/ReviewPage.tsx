import { useEffect, useState, useCallback } from 'react'
import { ChevronRight, BookOpenCheck, AlertCircle, Eye } from 'lucide-react'
import { m, AnimatePresence, useReducedMotion } from 'motion/react'
import { api, LearningItem } from '../api'
import PageHeader from '../components/PageHeader'
import { Skeleton } from '../components/ui/skeleton'
import { easeOut } from '../lib/animation'

const QUALITY_LABELS = [
    { label: 'AGAIN', q: 0, desc: 'Complete blackout', cls: 'text-[#EF4444] hover:border-[#EF4444] hover:text-[#EF4444]' },
    { label: 'HARD', q: 2, desc: 'Significant effort', cls: 'text-[#F59E0B] hover:border-[#F59E0B] hover:text-[#F59E0B]' },
    { label: 'GOOD', q: 4, desc: 'Correct with hesitation', cls: 'text-primary hover:border-primary hover:text-primary' },
    { label: 'EASY', q: 5, desc: 'Perfect recall', cls: 'text-primary hover:border-primary hover:text-primary' },
]

export default function ReviewPage() {
    const [dueItems, setDueItems] = useState<LearningItem[]>([])
    const [currentIdx, setCurrentIdx] = useState(0)
    const [revealed, setRevealed] = useState(false)
    const [loading, setLoading] = useState(true)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [done, setDone] = useState(false)
    const reduced = useReducedMotion()

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

    if (loading) {
        return (
            <div className="mx-auto w-full max-w-2xl space-y-4">
                <Skeleton className="h-3 w-48" />
                <div className="border border-border bg-card p-8">
                    <Skeleton className="mb-6 h-3 w-24" />
                    <Skeleton className="mb-8 h-8 w-3/4" />
                    <Skeleton className="h-11 w-full" />
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex h-full items-center justify-center gap-3 font-mono text-xs text-[#EF4444]">
                <AlertCircle size={16} strokeWidth={1.5} />
                Error — {error}
            </div>
        )
    }

    if (done) {
        return (
            <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
                <m.svg width="44" height="44" viewBox="0 0 24 24" fill="none" className="text-primary">
                    <m.path
                        d="M4.5 12.5L9.5 17.5L19.5 7"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="square"
                        initial={reduced ? false : { pathLength: 0 }}
                        animate={{ pathLength: 1 }}
                        transition={{ duration: 0.5, ease: easeOut }}
                    />
                </m.svg>
                <h2 className="font-sans text-xl text-foreground">Review Complete</h2>
                <p className="max-w-xs font-mono text-xs text-muted-foreground">
                    No items currently due for review. Well done — your memory is up to date.
                </p>
                <button
                    onClick={() => { setLoading(true); setDone(false); loadDue() }}
                    className="mt-4 border border-primary px-6 py-3 font-mono text-[11px] uppercase text-primary transition-colors hover:bg-primary/10"
                >
                    CHECK AGAIN
                </button>
            </div>
        )
    }

    const item = dueItems[currentIdx]
    const progress = Math.round((currentIdx / dueItems.length) * 100)

    return (
        <div className="flex flex-col items-center justify-center">
            <div className="w-full max-w-2xl space-y-4">
                <PageHeader
                    icon={BookOpenCheck}
                    title="Review"
                    subtitle="SM-2 spaced-repetition session"
                >
                    <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                        ITEM {currentIdx + 1} / {dueItems.length} DUE
                    </span>
                </PageHeader>

                {/* Progress bar */}
                <div className="h-[1px] w-full bg-slate-800">
                    <m.div
                        className="h-full bg-primary"
                        initial={false}
                        animate={{ width: `${progress}%` }}
                        transition={{ duration: 0.4, ease: easeOut }}
                    />
                </div>

                {/* Card */}
                <AnimatePresence mode="wait">
                    <m.div
                        key={item.id}
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={reduced ? undefined : { opacity: 0, y: -8 }}
                        transition={{ duration: 0.22, ease: easeOut }}
                        className="flex min-h-[320px] flex-col border border-border bg-card p-8 transition-shadow hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] [clip-path:polygon(0_0,calc(100%-16px)_0,100%_16px,100%_100%,0_100%)]"
                    >
                        {/* Meta tags */}
                        <div className="mb-6 flex gap-2">
                            <span className="border border-border px-2 py-0.5 font-mono text-[9px] uppercase text-muted-foreground">{item.difficulty}</span>
                            <span className="border border-border px-2 py-0.5 font-mono text-[9px] uppercase text-muted-foreground">{item.item_type}</span>
                            {item.success_rate > 0 && (
                                <span className="border border-primary/30 px-2 py-0.5 font-mono text-[9px] uppercase text-primary">
                                    {Math.round(item.success_rate)}% SUCCESS
                                </span>
                            )}
                        </div>

                        <h2 className="mb-auto font-sans text-xl text-foreground">{item.question}</h2>

                        {!revealed ? (
                            <m.button
                                onClick={() => setRevealed(true)}
                                whileTap={reduced ? undefined : { scale: 0.99 }}
                                transition={{ duration: 0.12 }}
                                className="mt-8 flex w-full items-center justify-center gap-2 border border-border py-3 font-mono text-[11px] uppercase text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                            >
                                <Eye size={14} strokeWidth={1.5} />
                                Reveal Answer <ChevronRight size={14} strokeWidth={1.5} />
                            </m.button>
                        ) : (
                            <>
                                <div className="mt-6 border border-border border-l-2 border-l-primary bg-background p-4 font-sans text-sm leading-relaxed text-muted-foreground">
                                    {item.answer}
                                </div>
                                <div className="mt-6 flex gap-[1px] bg-slate-800 p-[1px]">
                                    {QUALITY_LABELS.map(({ label, q, desc, cls }, i) => (
                                        <m.button
                                            key={label}
                                            disabled={submitting}
                                            onClick={() => handleRate(q)}
                                            title={desc}
                                            whileTap={reduced ? undefined : { scale: 0.97 }}
                                            initial={reduced ? false : { opacity: 0, y: 6 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: i * 0.05, duration: 0.2, ease: easeOut }}
                                            className={`flex-1 border border-transparent bg-card py-3 font-mono text-[10px] transition-colors disabled:cursor-wait disabled:opacity-40 ${cls}`}
                                        >
                                            {submitting ? '…' : label}
                                        </m.button>
                                    ))}
                                </div>
                            </>
                        )}
                    </m.div>
                </AnimatePresence>
            </div>
        </div>
    )
}
