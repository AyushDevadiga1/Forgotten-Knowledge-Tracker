import { useEffect, useState } from 'react'
import { io, Socket } from 'socket.io-client'
import { CheckCircle, XCircle, Zap, X } from 'lucide-react'
import { api, QuizQuestion } from '../api'

export default function MicroQuizModal() {
    const [quiz, setQuiz] = useState<QuizQuestion | null>(null)
    const [selected, setSelected] = useState<string | null>(null)
    const [answerState, setAnswerState] = useState<'idle' | 'correct' | 'wrong'>('idle')

    useEffect(() => {
        const socket: Socket = io()

        socket.on('connect', () => console.debug('FKT socket connected'))
        socket.on('disconnect', () => console.debug('FKT socket disconnected'))

        socket.on('micro_quiz', (data: QuizQuestion) => {
            if (data && data.concept && data.question) {
                setQuiz(data)
                setSelected(null)
                setAnswerState('idle')
            }
        })

        return () => { socket.disconnect() }
    }, [])

    const handleSelect = async (option: string) => {
        if (answerState !== 'idle' || !quiz) return
        setSelected(option)
        const correct = option === quiz.correct_answer
        setAnswerState(correct ? 'correct' : 'wrong')
        try {
            await api.submitQuizAnswer(quiz.concept, correct)
        } catch {
            // fire-and-forget — don't block the UI on a failed SM-2 write
        }
    }

    if (!quiz) return null

    const optionClass = (option: string) => {
        const base = 'w-full text-left px-4 py-3 border font-mono text-xs transition-all duration-200 '
        if (answerState === 'idle')
            return base + 'border-fkt-elevated text-fkt-text-primary hover:border-fkt-accent hover:text-fkt-accent bg-fkt-base cursor-pointer'
        if (option === quiz.correct_answer)
            return base + 'border-fkt-accent text-fkt-accent bg-fkt-accent/5 cursor-default'
        if (option === selected && answerState === 'wrong')
            return base + 'border-[#EF4444] text-[#EF4444] bg-[#EF4444]/5 cursor-default'
        return base + 'border-fkt-elevated text-fkt-text-dim cursor-default opacity-50'
    }

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-lg bg-fkt-surface border border-fkt-accent/40 shadow-2xl animate-in zoom-in-95">
                {/* Header */}
                <div className="px-5 py-3 border-b border-fkt-elevated bg-fkt-base flex items-center justify-between">
                    <span className="text-[10px] font-mono uppercase tracking-widest text-fkt-text-dim flex items-center gap-2">
                        <Zap size={11} className="text-fkt-accent" />
                        Micro-Quiz
                        <span className="text-fkt-text-dim/60">· pushed live</span>
                    </span>
                    <button
                        onClick={() => setQuiz(null)}
                        title="Close"
                        className="text-fkt-text-dim hover:text-fkt-text-primary transition-colors"
                    >
                        <X size={16} />
                    </button>
                </div>

                {/* Body */}
                <div className="p-5">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-[10px] font-mono uppercase tracking-widest text-fkt-text-muted">
                            Concept: <span className="text-fkt-accent">{quiz.concept}</span>
                        </span>
                        <span className="text-[9px] font-mono text-fkt-text-dim uppercase">{quiz.difficulty}</span>
                    </div>

                    <p className="text-sm text-fkt-text-primary font-sans leading-relaxed mb-6">
                        {quiz.question}
                    </p>

                    <div className="space-y-2">
                        {quiz.options.map((opt, i) => (
                            <button
                                key={i}
                                className={optionClass(opt)}
                                onClick={() => handleSelect(opt)}
                                disabled={answerState !== 'idle'}
                            >
                                <span className="text-fkt-text-dim mr-3">{String.fromCharCode(65 + i)}.</span>
                                {opt}
                            </button>
                        ))}
                    </div>

                    {answerState !== 'idle' && (
                        <div className={`mt-5 p-3 border flex items-center gap-3 ${
                            answerState === 'correct'
                                ? 'border-fkt-accent bg-fkt-accent/5'
                                : 'border-[#EF4444] bg-[#EF4444]/5'
                        }`}>
                            {answerState === 'correct'
                                ? <CheckCircle size={16} className="text-fkt-accent shrink-0" />
                                : <XCircle size={16} className="text-[#EF4444] shrink-0" />
                            }
                            <div className="flex-1">
                                <p className="text-xs font-mono text-fkt-text-primary">
                                    {answerState === 'correct'
                                        ? 'Correct! SM-2 interval extended.'
                                        : `Incorrect. Correct answer: ${quiz.correct_answer}`}
                                </p>
                            </div>
                            <button
                                onClick={() => setQuiz(null)}
                                className="text-[10px] font-mono uppercase tracking-widest border border-fkt-elevated px-3 py-1.5
                                           hover:border-fkt-accent hover:text-fkt-accent transition-colors text-fkt-text-muted"
                            >
                                Close
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
