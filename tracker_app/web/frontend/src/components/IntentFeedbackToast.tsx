import { useEffect, useState } from 'react'
import { api, IntentPrediction } from '../api'

export default function IntentFeedbackToast() {
    const [prediction, setPrediction] = useState<IntentPrediction | null>(null)
    const [submitted, setSubmitted] = useState(false)
    const [actualIntent, setActualIntent] = useState('')

    useEffect(() => {
        // Poll every 10 seconds for the latest prediction
        const checkRecent = async () => {
            try {
                const res = await api.getRecentIntent()
                const data = res.data
                // Only prompt if it exists and hasn't been given feedback yet
                if (data && data.user_feedback === null) {
                    setPrediction(data)
                    setSubmitted(false)
                    setActualIntent('')
                } else {
                    setPrediction(null)
                }
            } catch (e) {
                console.error('Failed to fetch recent intent', e)
            }
        }

        checkRecent()
        const interval = setInterval(checkRecent, 10000)
        return () => clearInterval(interval)
    }, [submitted]) // Re-run if submitted changes, though interval handles it

    const handleFeedback = async (isCorrect: boolean) => {
        if (!prediction) return
        try {
            await api.sendIntentFeedback(prediction.id, isCorrect, !isCorrect && actualIntent ? actualIntent : undefined)
            setSubmitted(true)
            // Hide immediately
            setPrediction(null)
        } catch (e) {
            console.error('Failed to submit feedback', e)
        }
    }

    if (!prediction) return null

    return (
        <div className="fixed bottom-6 right-6 w-80 bg-fkt-surface border border-fkt-elevated shadow-2xl z-50 animate-in slide-in-from-bottom-5">
            <div className="p-3 border-b border-fkt-elevated bg-fkt-base flex justify-between items-center">
                <span className="text-[10px] uppercase tracking-widest text-fkt-text-muted font-mono flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-fkt-accent animate-pulse" />
                    DATA COLLECTION
                </span>
                <span className="text-[9px] text-fkt-text-dim font-mono">{Math.round(prediction.confidence * 100)}% CONF</span>
            </div>

            <div className="p-4">
                <p className="text-xs text-fkt-text-muted mb-3 font-sans">
                    The system predicted your recent activity as:
                </p>
                <div className="text-center font-mono text-fkt-accent text-lg mb-4 uppercase">
                    {prediction.predicted_intent}
                </div>

                <p className="text-[10px] text-fkt-text-muted mb-2 uppercase tracking-wide">Was this correct?</p>
                <div className="flex gap-2 mb-3">
                    <button
                        onClick={() => handleFeedback(true)}
                        className="flex-1 py-2 border border-fkt-elevated hover:border-fkt-accent hover:text-fkt-accent text-fkt-text-primary transition-colors text-xs font-mono bg-fkt-base"
                    >
                        YES
                    </button>
                    <button
                        onClick={() => handleFeedback(false)}
                        className="flex-1 py-2 border border-fkt-elevated hover:border-[#EF4444] hover:text-[#EF4444] text-fkt-text-primary transition-colors text-xs font-mono bg-fkt-base"
                    >
                        NO
                    </button>
                </div>

                {/* Optional correction field to improve data */}
                <div className="mt-2 pt-2 border-t border-fkt-elevated/50">
                    <input
                        type="text"
                        placeholder="If no, what were you doing?"
                        value={actualIntent}
                        onChange={e => setActualIntent(e.target.value)}
                        className="w-full bg-transparent border border-fkt-elevated p-2 text-[11px] font-mono outline-none focus:border-[#F59E0B] text-fkt-text-primary placeholder:text-fkt-text-dim"
                    />
                </div>
            </div>
        </div>
    )
}
