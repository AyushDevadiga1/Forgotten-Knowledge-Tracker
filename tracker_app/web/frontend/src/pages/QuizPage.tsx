import { useEffect, useState, useCallback } from 'react'
import { Zap, CheckCircle, XCircle, AlertTriangle, Loader, RefreshCw } from 'lucide-react'
import { api, QuizQuestion } from '../api'

type AnswerState = 'idle' | 'correct' | 'wrong'

function BackendDown() {
    return (
        <div className="flex flex-col items-center justify-center h-64 gap-4 text-fkt-text-muted">
            <AlertTriangle size={40} strokeWidth={1} className="text-[#EF4444]" />
            <p className="text-sm font-mono">Backend offline — start <code className="text-fkt-accent">main.py</code> and <code className="text-fkt-accent">web/app.py</code></p>
            <p className="text-[11px] text-fkt-text-dim">Quiz questions will appear once the tracker is running.</p>
        </div>
    )
}

function NoQuiz({ onRefresh, refreshing }: { onRefresh: () => void; refreshing: boolean }) {
    return (
        <div className="flex flex-col items-center justify-center h-64 gap-4 text-fkt-text-muted">
            <Zap size={40} strokeWidth={1} className="text-fkt-text-dim" />
            <p className="text-sm font-mono text-fkt-text-primary">No quiz available right now</p>
            <p className="text-[11px] text-fkt-text-dim text-center max-w-xs">
                Quizzes are generated from your tracked concepts. Browse the web or study with the tracker running — a quiz will appear when a concept is overdue for review.
            </p>
            <button
                id="quiz-refresh-btn"
                onClick={onRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest border border-fkt-elevated px-4 py-2
                           hover:border-fkt-accent hover:text-fkt-accent transition-colors text-fkt-text-muted"
            >
                <RefreshCw size={11} className={refreshing ? 'animate-spin' : ''} />
                Check again
            </button>
        </div>
    )
}

export default function QuizPage() {
    const [quiz, setQuiz] = useState<QuizQuestion | null>(null)
    const [loading, setLoading] = useState(true)
    const [backendDown, setBackendDown] = useState(false)
    const [refreshing, setRefreshing] = useState(false)
    const [selected, setSelected] = useState<string | null>(null)
    const [answerState, setAnswerState] = useState<AnswerState>('idle')
    const [score, setScore] = useState({ correct: 0, wrong: 0 })

    const fetchQuiz = useCallback(async (isRefresh = false) => {
        if (isRefresh) setRefreshing(true)
        try {
            const res = await api.getQuiz()
            setQuiz(res.data)
            setSelected(null)
            setAnswerState('idle')
            setBackendDown(false)
        } catch {
            setBackendDown(true)
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }, [])

    useEffect(() => { fetchQuiz() }, [fetchQuiz])

    const handleSelect = async (option: string) => {
        if (answerState !== 'idle' || !quiz) return
        setSelected(option)
        const correct = option === quiz.correct_answer
        setAnswerState(correct ? 'correct' : 'wrong')
        setScore(s => correct ? { ...s, correct: s.correct + 1 } : { ...s, wrong: s.wrong + 1 })
        try {
            await api.submitQuizAnswer(quiz.concept, correct)
        } catch {
            // fire-and-forget — don't block the UI
        }
    }

    const handleNext = () => fetchQuiz(true)

    const optionClass = (option: string) => {
        const base = 'w-full text-left px-4 py-3 border font-mono text-xs transition-all duration-200 '
        if (answerState === 'idle')
            return base + 'border-fkt-elevated text-fkt-text-primary hover:border-fkt-accent hover:text-fkt-accent bg-fkt-base cursor-pointer'
        if (option === quiz?.correct_answer)
            return base + 'border-fkt-accent text-fkt-accent bg-fkt-accent/5 cursor-default'
        if (option === selected && answerState === 'wrong')
            return base + 'border-[#EF4444] text-[#EF4444] bg-[#EF4444]/5 cursor-default'
        return base + 'border-fkt-elevated text-fkt-text-dim cursor-default opacity-50'
    }

    if (loading) return (
        <div className="flex items-center justify-center h-64 gap-3 text-fkt-text-muted">
            <Loader size={18} className="animate-spin" />
            <span className="text-xs font-mono">Generating quiz…</span>
        </div>
    )

    if (backendDown) return <BackendDown />

    return (
        <div className="max-w-xl mx-auto space-y-5">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-fkt-text-primary font-mono text-sm uppercase tracking-widest flex items-center gap-2">
                        <Zap size={14} className="text-fkt-accent" />
                        Micro-Quiz
                    </h1>
                    <p className="text-[11px] text-fkt-text-dim mt-0.5 font-mono">
                        SM-2 spaced repetition quiz from your tracked concepts
                    </p>
                </div>
                {/* Score */}
                <div className="flex gap-3 text-[10px] font-mono">
                    <span className="text-fkt-accent flex items-center gap-1">
                        <CheckCircle size={11} /> {score.correct}
                    </span>
                    <span className="text-[#EF4444] flex items-center gap-1">
                        <XCircle size={11} /> {score.wrong}
                    </span>
                </div>
            </div>

            {!quiz
                ? <NoQuiz onRefresh={() => fetchQuiz(true)} refreshing={refreshing} />
                : (
                    <div className="bg-fkt-surface border border-fkt-elevated">
                        {/* Quiz header */}
                        <div className="px-5 py-3 border-b border-fkt-elevated bg-fkt-base flex items-center justify-between">
                            <span className="text-[10px] font-mono uppercase tracking-widest text-fkt-text-dim flex items-center gap-2">
                                <div className="w-1.5 h-1.5 bg-fkt-accent animate-pulse" />
                                Concept: <span className="text-fkt-accent">{quiz.concept}</span>
                            </span>
                            <span className="text-[9px] font-mono text-fkt-text-dim uppercase">{quiz.difficulty}</span>
                        </div>

                        {/* Question */}
                        <div className="p-5">
                            <p className="text-sm text-fkt-text-primary font-sans leading-relaxed mb-6">
                                {quiz.question}
                            </p>

                            {/* Options */}
                            <div id="quiz-options" className="space-y-2">
                                {quiz.options.map((opt, i) => (
                                    <button
                                        key={i}
                                        id={`quiz-option-${i}`}
                                        className={optionClass(opt)}
                                        onClick={() => handleSelect(opt)}
                                        disabled={answerState !== 'idle'}
                                    >
                                        <span className="text-fkt-text-dim mr-3">{String.fromCharCode(65 + i)}.</span>
                                        {opt}
                                    </button>
                                ))}
                            </div>

                            {/* Result banner */}
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
                                        id="quiz-next-btn"
                                        onClick={handleNext}
                                        disabled={refreshing}
                                        className="text-[10px] font-mono uppercase tracking-widest border border-fkt-elevated px-3 py-1.5
                                                   hover:border-fkt-accent hover:text-fkt-accent transition-colors text-fkt-text-muted flex items-center gap-1"
                                    >
                                        <RefreshCw size={10} className={refreshing ? 'animate-spin' : ''} />
                                        Next
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                )
            }
        </div>
    )
}
