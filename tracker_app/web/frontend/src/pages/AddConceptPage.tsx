import { useState } from 'react'
import { Loader, CheckCircle, AlertCircle, PlusCircle } from 'lucide-react'
import { m, AnimatePresence, useReducedMotion } from 'motion/react'
import { api } from '../api'
import PageHeader from '../components/PageHeader'
import { spring } from '@/lib/animation'
import { cn } from '@/lib/utils'

type Status = 'idle' | 'loading' | 'success' | 'error'

const DIFFICULTIES = ['easy', 'medium', 'hard'] as const
const TYPES = ['concept', 'definition', 'code', 'procedure', 'fact'] as const

const fieldCls =
    'w-full border border-border bg-background p-3 font-sans text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary'

const selectCls =
    'w-full border border-border bg-background p-3 font-mono text-[12px] text-foreground outline-none transition-colors focus:border-primary'

export default function AddConceptPage() {
    const [form, setForm] = useState({
        question: '',
        answer: '',
        difficulty: 'medium',
        item_type: 'concept',
        tags: '',
    })
    const [status, setStatus] = useState<Status>('idle')
    const [errorMsg, setErrorMsg] = useState('')
    const reduced = useReducedMotion()

    const set = (field: keyof typeof form) =>
        (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
            setForm((prev) => ({ ...prev, [field]: e.target.value }))

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!form.question.trim() || !form.answer.trim()) return

        setStatus('loading')
        setErrorMsg('')
        try {
            await api.createItem({
                question: form.question.trim(),
                answer: form.answer.trim(),
                difficulty: form.difficulty,
                item_type: form.item_type,
                tags: form.tags.split(',').map((t) => t.trim()).filter(Boolean),
            })
            setStatus('success')
            setForm({ question: '', answer: '', difficulty: 'medium', item_type: 'concept', tags: '' })
            setTimeout(() => setStatus('idle'), 3000)
        } catch (e) {
            setErrorMsg(e instanceof Error ? e.message : 'Submission failed')
            setStatus('error')
        }
    }

    return (
        <div className="flex flex-col items-center justify-center">
            <div className="w-full max-w-xl">
                <PageHeader
                    icon={PlusCircle}
                    title="Add Concept"
                    subtitle="Manual ingestion into the spaced-repetition deck"
                />

                <m.div
                    initial={reduced ? false : { opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={spring}
                    className="border border-border bg-card p-8 transition-shadow hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] [clip-path:polygon(0_0,calc(100%-12px)_0,100%_12px,100%_100%,0_100%)]"
                >
                    <h2 className="mb-8 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                        Manual Ingestion
                    </h2>

                    <AnimatePresence>
                        {status === 'success' && (
                            <m.div
                                initial={{ opacity: 0, y: -6 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="mb-6 flex items-center gap-2 border border-primary/30 bg-primary/5 p-3 font-mono text-xs text-primary"
                            >
                                <CheckCircle size={14} strokeWidth={1.5} /> Item ingested successfully
                            </m.div>
                        )}
                        {status === 'error' && (
                            <m.div
                                initial={{ opacity: 0, y: -6 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="mb-6 flex items-center gap-2 border border-[#EF4444]/30 bg-[#EF4444]/5 p-3 font-mono text-xs text-[#EF4444]"
                            >
                                <AlertCircle size={14} strokeWidth={1.5} /> {errorMsg}
                            </m.div>
                        )}
                    </AnimatePresence>

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-2">
                            <label className="block font-mono text-[10px] text-muted-foreground">QUESTION / TOPIC *</label>
                            <input
                                required
                                value={form.question}
                                onChange={set('question')}
                                className={fieldCls}
                                placeholder="e.g. What is the Big-O complexity of quicksort?"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="block font-mono text-[10px] text-muted-foreground">ANSWER / EXPLANATION *</label>
                            <textarea
                                required
                                value={form.answer}
                                onChange={set('answer')}
                                className={cn(fieldCls, 'h-28 resize-none')}
                                placeholder="e.g. Average O(n log n), worst case O(n²)."
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="block font-mono text-[10px] text-muted-foreground">DIFFICULTY</label>
                                <select value={form.difficulty} onChange={set('difficulty')} className={selectCls}>
                                    {DIFFICULTIES.map((d) => <option key={d} value={d}>{d.toUpperCase()}</option>)}
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="block font-mono text-[10px] text-muted-foreground">TYPE</label>
                                <select value={form.item_type} onChange={set('item_type')} className={selectCls}>
                                    {TYPES.map((t) => <option key={t} value={t}>{t.toUpperCase()}</option>)}
                                </select>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="block font-mono text-[10px] text-muted-foreground">
                                TAGS <span className="opacity-50">(comma separated)</span>
                            </label>
                            <input
                                value={form.tags}
                                onChange={set('tags')}
                                className={fieldCls}
                                placeholder="algorithms, cs, python"
                            />
                        </div>

                        <m.button
                            type="submit"
                            disabled={status === 'loading'}
                            whileTap={reduced ? undefined : { scale: 0.99 }}
                            transition={{ duration: 0.1 }}
                            className="mt-2 flex w-full items-center justify-center gap-2 border border-primary bg-primary/10 py-4 font-mono text-[12px] uppercase text-primary transition-colors hover:bg-primary/20 disabled:cursor-wait disabled:opacity-50"
                        >
                            {status === 'loading'
                                ? <><Loader size={14} strokeWidth={1.5} className="animate-spin" /> INGESTING…</>
                                : 'INGEST ITEM'}
                        </m.button>
                    </form>
                </m.div>
            </div>
        </div>
    )
}
