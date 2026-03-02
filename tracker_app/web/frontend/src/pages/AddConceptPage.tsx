import { useState } from 'react'
import { Loader, CheckCircle, AlertCircle } from 'lucide-react'
import { api } from '../api'

type Status = 'idle' | 'loading' | 'success' | 'error'

const DIFFICULTIES = ['easy', 'medium', 'hard'] as const
const TYPES = ['concept', 'definition', 'code', 'procedure', 'fact'] as const

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

    const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
        setForm(prev => ({ ...prev, [field]: e.target.value }))

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
                tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
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
        <div className="flex flex-col items-center justify-center h-full">
            <div className="w-full max-w-xl bg-fkt-surface border border-fkt-elevated p-8 hover:shadow-[inset_0_0_0_1px_rgba(0,255,163,0.2)] transition-shadow [clip-path:polygon(0_0,calc(100%-12px)_0,100%_12px,100%_100%,0_100%)]">

                <h2 className="text-[10px] uppercase tracking-[0.12em] text-fkt-text-muted mb-8 font-mono">
                    MANUAL INGESTION — ADD CONCEPT
                </h2>

                {status === 'success' && (
                    <div className="flex items-center gap-2 mb-6 p-3 border border-fkt-accent/30 bg-fkt-accent/5 text-fkt-accent font-mono text-xs">
                        <CheckCircle size={14} strokeWidth={1.5} /> Item ingested successfully
                    </div>
                )}
                {status === 'error' && (
                    <div className="flex items-center gap-2 mb-6 p-3 border border-[#EF4444]/30 bg-[#EF4444]/5 text-[#EF4444] font-mono text-xs">
                        <AlertCircle size={14} strokeWidth={1.5} /> {errorMsg}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div className="space-y-2">
                        <label className="text-[10px] font-mono text-fkt-text-muted block">QUESTION / TOPIC *</label>
                        <input
                            required
                            value={form.question}
                            onChange={set('question')}
                            className="w-full bg-fkt-base border border-fkt-elevated p-3 text-sm text-fkt-text-primary outline-none focus:border-fkt-accent transition-colors placeholder:text-fkt-text-dim"
                            placeholder="e.g. What is the Big-O complexity of quicksort?"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-[10px] font-mono text-fkt-text-muted block">ANSWER / EXPLANATION *</label>
                        <textarea
                            required
                            value={form.answer}
                            onChange={set('answer')}
                            className="w-full h-28 bg-fkt-base border border-fkt-elevated p-3 text-sm text-fkt-text-primary outline-none focus:border-fkt-accent transition-colors resize-none placeholder:text-fkt-text-dim"
                            placeholder="e.g. Average O(n log n), worst case O(n²)."
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-mono text-fkt-text-muted block">DIFFICULTY</label>
                            <select value={form.difficulty} onChange={set('difficulty')} className="w-full bg-fkt-base border border-fkt-elevated p-3 text-[12px] font-mono text-fkt-text-primary outline-none focus:border-fkt-accent transition-colors">
                                {DIFFICULTIES.map(d => <option key={d} value={d}>{d.toUpperCase()}</option>)}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-mono text-fkt-text-muted block">TYPE</label>
                            <select value={form.item_type} onChange={set('item_type')} className="w-full bg-fkt-base border border-fkt-elevated p-3 text-[12px] font-mono text-fkt-text-primary outline-none focus:border-fkt-accent transition-colors">
                                {TYPES.map(t => <option key={t} value={t}>{t.toUpperCase()}</option>)}
                            </select>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-[10px] font-mono text-fkt-text-muted block">TAGS <span className="opacity-50">(comma separated)</span></label>
                        <input
                            value={form.tags}
                            onChange={set('tags')}
                            className="w-full bg-fkt-base border border-fkt-elevated p-3 text-sm text-fkt-text-primary outline-none focus:border-fkt-accent transition-colors placeholder:text-fkt-text-dim"
                            placeholder="algorithms, cs, python"
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={status === 'loading'}
                        className="w-full mt-2 py-4 border border-fkt-accent bg-fkt-accent/10 text-fkt-accent text-[12px] font-mono uppercase hover:bg-fkt-accent/20 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-wait"
                    >
                        {status === 'loading'
                            ? <><Loader size={14} strokeWidth={1.5} className="animate-spin" /> INGESTING…</>
                            : 'INGEST ITEM'
                        }
                    </button>
                </form>

            </div>
        </div>
    )
}
