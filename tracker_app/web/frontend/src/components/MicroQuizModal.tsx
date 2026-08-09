import { useEffect, useState } from 'react'
import { io, Socket } from 'socket.io-client'
import { m, AnimatePresence, useReducedMotion } from 'motion/react'
import { Zap, X } from 'lucide-react'
import { QuizQuestion } from '../api'
import QuizOptionList from './QuizOptionList'
import DifficultyBadge from './DifficultyBadge'
import { spring } from '@/lib/animation'

/** Live-pushed quiz modal (Socket.IO micro_quiz). The card springs in on a
 * Bklit-style curve; only this shell + the shared QuizOptionList drive it. */
export default function MicroQuizModal() {
    const [quiz, setQuiz] = useState<QuizQuestion | null>(null)
    const reduced = useReducedMotion()

    useEffect(() => {
        const socket: Socket = io()

        socket.on('connect', () => console.debug('FKT socket connected'))
        socket.on('disconnect', () => console.debug('FKT socket disconnected'))

        socket.on('micro_quiz', (data: QuizQuestion) => {
            if (data && data.concept && data.question) {
                setQuiz(data)
            }
        })

        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') setQuiz(null)
        }
        window.addEventListener('keydown', onKey)
        return () => {
            socket.disconnect()
            window.removeEventListener('keydown', onKey)
        }
    }, [])

    return (
        <AnimatePresence>
            {quiz && (
                <m.div
                    key="micro-quiz"
                    className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm"
                    initial={reduced ? false : { opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.18 }}
                    onClick={() => setQuiz(null)}
                >
                    <m.div
                        className="w-full max-w-lg border border-primary/40 bg-card shadow-[0_0_48px_rgba(0,255,163,0.12)]"
                        onClick={(e) => e.stopPropagation()}
                        initial={reduced ? false : { scale: 0.94, y: 16, opacity: 0 }}
                        animate={{ scale: 1, y: 0, opacity: 1 }}
                        exit={reduced ? undefined : { scale: 0.96, y: 8, opacity: 0 }}
                        transition={spring}
                    >
                        <div className="flex items-center justify-between border-b border-border bg-background px-5 py-3">
                            <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                                <Zap size={11} className="text-primary" />
                                Micro-Quiz
                                <span className="text-muted-foreground/60">· pushed live</span>
                            </span>
                            <button
                                onClick={() => setQuiz(null)}
                                title="Close"
                                aria-label="Close quiz"
                                className="text-muted-foreground transition-colors hover:text-foreground"
                            >
                                <X size={16} />
                            </button>
                        </div>

                        <div className="p-5">
                            <div className="mb-4 flex items-center justify-between">
                                <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                                    Concept: <span className="text-primary">{quiz.concept}</span>
                                </span>
                                <DifficultyBadge difficulty={quiz.difficulty} />
                            </div>

                            <p className="mb-6 font-sans text-sm leading-relaxed text-foreground">
                                {quiz.question}
                            </p>

                            <QuizOptionList
                                quiz={quiz}
                                action={
                                    <button
                                        onClick={() => setQuiz(null)}
                                        className="border border-border px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                                    >
                                        Close
                                    </button>
                                }
                            />
                        </div>
                    </m.div>
                </m.div>
            )}
        </AnimatePresence>
    )
}
