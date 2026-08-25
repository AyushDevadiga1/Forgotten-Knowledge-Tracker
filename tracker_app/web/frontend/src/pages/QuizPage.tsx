import { useEffect, useState, useCallback } from 'react'
import { Zap, CheckCircle, XCircle, RefreshCw } from 'lucide-react'
import { m } from 'motion/react'
import { api, QuizQuestion } from '../api'
import PageHeader from '../components/PageHeader'
import QuizOptionList from '../components/QuizOptionList'
import FlashcardView from '../components/FlashcardView'
import FillBlankView from '../components/FillBlankView'
import DifficultyBadge from '../components/DifficultyBadge'
import EmptyState from '../components/EmptyState'
import { QuizSkeleton } from '../components/PageSkeleton'
import BackendDown from '../components/BackendDown'
import { easeOut } from '../lib/animation'

export default function QuizPage() {
    const [quiz, setQuiz] = useState<QuizQuestion | null>(null)
    const [loading, setLoading] = useState(true)
    const [backendDown, setBackendDown] = useState(false)
    const [refreshing, setRefreshing] = useState(false)
    const [score, setScore] = useState({ correct: 0, wrong: 0 })
    const [asked, setAsked] = useState(0)

    const fetchQuiz = useCallback(async (isRefresh = false) => {
        if (isRefresh) setRefreshing(true)
        try {
            const res = await api.getQuiz()
            setQuiz(res.data)
            setBackendDown(false)
        } catch {
            setBackendDown(true)
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }, [])

    useEffect(() => { fetchQuiz() }, [fetchQuiz])

    const handleNext = () => fetchQuiz(true)

    if (loading) return <QuizSkeleton />
    if (backendDown) return <BackendDown />

    return (
        <div className="mx-auto max-w-xl space-y-5">
            <PageHeader
                icon={Zap}
                title="Micro-Quiz"
                subtitle="SM-2 spaced-repetition quiz from your tracked concepts"
            >
                <div className="flex items-center gap-3 font-mono text-[10px]">
                    <span className="flex items-center gap-1 text-primary">
                        <CheckCircle size={11} /> {score.correct}
                    </span>
                    <span className="flex items-center gap-1 text-[#EF4444]">
                        <XCircle size={11} /> {score.wrong}
                    </span>
                    {asked > 0 && <span className="text-muted-foreground">/ {asked}</span>}
                </div>
            </PageHeader>

            {!quiz ? (
                <div className="space-y-3">
                    <EmptyState
                        label="No quiz available right now"
                        hint="Quizzes are generated from your tracked concepts. Study with the tracker running — a quiz appears when a concept is overdue for review."
                    />
                    <div className="flex justify-center">
                        <button
                            id="quiz-refresh-btn"
                            onClick={() => fetchQuiz(true)}
                            disabled={refreshing}
                            className="flex items-center gap-2 border border-border px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                        >
                            <RefreshCw size={11} className={refreshing ? 'animate-spin' : ''} />
                            Check again
                        </button>
                    </div>
                </div>
            ) : (
                <m.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.22, ease: easeOut }}
                    className="border border-border bg-card"
                >
                    <div className="flex items-center justify-between border-b border-border bg-background px-5 py-3">
                        <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                            <span className="h-1.5 w-1.5 animate-pulse bg-primary" />
                            Concept: <span className="text-primary">{quiz.concept}</span>
                        </span>
                        <DifficultyBadge difficulty={quiz.difficulty} />
                    </div>

                    <div className="p-5">
                        <m.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.2, delay: 0.05, ease: easeOut }}
                            className="mb-6 font-sans text-sm leading-relaxed text-foreground"
                        >
                            {quiz.question}
                        </m.p>

                        {(!quiz.quiz_type || quiz.quiz_type === 'multiple_choice') ? (
                            <QuizOptionList
                                quiz={quiz}
                                onAnswer={(correct) => {
                                    setAsked((a) => a + 1)
                                    setScore((s) =>
                                        correct ? { ...s, correct: s.correct + 1 } : { ...s, wrong: s.wrong + 1 }
                                    )
                                }}
                                action={
                                    <button
                                        id="quiz-next-btn"
                                        onClick={handleNext}
                                        disabled={refreshing}
                                        className="flex items-center gap-1 border border-border px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                                    >
                                        <RefreshCw size={10} className={refreshing ? 'animate-spin' : ''} />
                                        Next
                                    </button>
                                }
                            />
                        ) : quiz.quiz_type === 'flashcard' ? (
                            <FlashcardView
                                quiz={quiz}
                                onAnswer={(correct) => {
                                    setAsked((a) => a + 1)
                                    setScore((s) =>
                                        correct ? { ...s, correct: s.correct + 1 } : { ...s, wrong: s.wrong + 1 }
                                    )
                                }}
                                action={
                                    <button
                                        id="quiz-next-btn"
                                        onClick={handleNext}
                                        disabled={refreshing}
                                        className="flex items-center gap-1 border border-border px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                                    >
                                        <RefreshCw size={10} className={refreshing ? 'animate-spin' : ''} />
                                        Next
                                    </button>
                                }
                            />
                        ) : (
                            <FillBlankView
                                quiz={quiz}
                                onAnswer={(correct) => {
                                    setAsked((a) => a + 1)
                                    setScore((s) =>
                                        correct ? { ...s, correct: s.correct + 1 } : { ...s, wrong: s.wrong + 1 }
                                    )
                                }}
                                action={
                                    <button
                                        id="quiz-next-btn"
                                        onClick={handleNext}
                                        disabled={refreshing}
                                        className="flex items-center gap-1 border border-border px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                                    >
                                        <RefreshCw size={10} className={refreshing ? 'animate-spin' : ''} />
                                        Next
                                    </button>
                                }
                            />
                        )}
                    </div>
                </m.div>
            )}
        </div>
    )
}
