import { useEffect, useState } from 'react'
import { io, Socket } from 'socket.io-client'
import { Zap, X } from 'lucide-react'
import { QuizQuestion } from '../api'
import { useQuizAnswer } from '../hooks/useQuizAnswer'
import QuizResultBanner from './QuizResultBanner'

export default function MicroQuizModal() {
    const [quiz, setQuiz] = useState<QuizQuestion | null>(null)
    const { answerState, reset, handleSelect, optionClass } = useQuizAnswer()

    useEffect(() => {
        const socket: Socket = io()

        socket.on('connect', () => console.debug('FKT socket connected'))
        socket.on('disconnect', () => console.debug('FKT socket disconnected'))

        socket.on('micro_quiz', (data: QuizQuestion) => {
            if (data && data.concept && data.question) {
                setQuiz(data)
                reset()
            }
        })

        return () => { socket.disconnect() }
    }, [reset])

    if (!quiz) return null

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
                                className={optionClass(quiz, opt)}
                                onClick={() => handleSelect(quiz, opt)}
                                disabled={answerState !== 'idle'}
                            >
                                <span className="text-fkt-text-dim mr-3">{String.fromCharCode(65 + i)}.</span>
                                {opt}
                            </button>
                        ))}
                    </div>

                    <QuizResultBanner
                        quiz={quiz}
                        answerState={answerState}
                        action={
                            <button
                                onClick={() => setQuiz(null)}
                                className="text-[10px] font-mono uppercase tracking-widest border border-fkt-elevated px-3 py-1.5
                                           hover:border-fkt-accent hover:text-fkt-accent transition-colors text-fkt-text-muted"
                            >
                                Close
                            </button>
                        }
                    />
                </div>
            </div>
        </div>
    )
}
