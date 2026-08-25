import { useState } from 'react'
import { m } from 'motion/react'
import { CheckCircle, XCircle } from 'lucide-react'
import type { QuizQuestion } from '@/api'
import { cn } from '@/lib/utils'

interface FillBlankViewProps {
    quiz: QuizQuestion
    onAnswer: (correct: boolean) => void
    action: React.ReactNode
}

export default function FillBlankView({ quiz, onAnswer, action }: FillBlankViewProps) {
    const [input, setInput] = useState('')
    const [submitted, setSubmitted] = useState(false)
    const [wasCorrect, setWasCorrect] = useState(false)

    const handleSubmit = () => {
        if (!input.trim()) return
        const correct = input.trim().toLowerCase() === quiz.correct_answer.toLowerCase()
        setWasCorrect(correct)
        setSubmitted(true)
        onAnswer(correct)
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !submitted) handleSubmit()
    }

    return (
        <div className="space-y-4">
            <m.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.2 }}
                className="border border-border bg-background p-6"
            >
                <p className="font-sans text-sm leading-relaxed text-foreground">
                    {quiz.question}
                </p>

                <div className="mt-4 flex items-center gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={submitted}
                        placeholder="Type your answer..."
                        autoFocus
                        className={cn(
                            'flex-1 border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1',
                            submitted
                                ? wasCorrect
                                    ? 'border-primary/40 focus:ring-primary'
                                    : 'border-red-500/40 focus:ring-red-500'
                                : 'border-border focus:ring-primary'
                        )}
                    />
                    {!submitted && (
                        <button
                            onClick={handleSubmit}
                            disabled={!input.trim()}
                            className="border border-border px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground transition-colors hover:border-primary hover:text-primary disabled:opacity-40"
                        >
                            Check
                        </button>
                    )}
                </div>

                {submitted && (
                    <m.div
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.15 }}
                        className={cn(
                            'mt-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest',
                            wasCorrect ? 'text-primary' : 'text-red-500'
                        )}
                    >
                        {wasCorrect ? <CheckCircle size={12} /> : <XCircle size={12} />}
                        {wasCorrect ? 'Correct!' : 'Answer: ' + quiz.correct_answer}
                    </m.div>
                )}
            </m.div>

            {submitted && (
                <div className="flex justify-end">
                    {action}
                </div>
            )}
        </div>
    )
}
