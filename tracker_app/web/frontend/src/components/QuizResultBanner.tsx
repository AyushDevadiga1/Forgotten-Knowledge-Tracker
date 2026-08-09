import { m, useReducedMotion } from 'motion/react'
import { XCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import type { QuizQuestion } from '../api'
import type { AnswerState } from '../hooks/useQuizAnswer'
import { cn } from '@/lib/utils'
import { easeOut } from '@/lib/animation'

// Shared quiz result banner (M-3). The only difference between QuizPage and
// MicroQuizModal is the trailing action button, which callers pass as `action`.
// Renders nothing while idle; draws an animated checkmark when correct.
export default function QuizResultBanner({ quiz, answerState, action }: {
    quiz: QuizQuestion
    answerState: AnswerState
    action?: ReactNode
}) {
    const reduced = useReducedMotion()
    if (answerState === 'idle') return null

    const correct = answerState === 'correct'
    return (
        <m.div
            initial={reduced ? false : { opacity: 0, y: 8, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.2, ease: easeOut }}
            className={cn(
                'mt-5 flex items-center gap-3 border p-3',
                correct ? 'border-primary bg-primary/5' : 'border-destructive bg-destructive/5'
            )}
        >
            {correct ? (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="shrink-0 text-primary">
                    <m.path
                        d="M3 8.5L6.5 12L13 4.5"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="square"
                        initial={reduced ? false : { pathLength: 0 }}
                        animate={{ pathLength: 1 }}
                        transition={{ duration: 0.3, ease: easeOut }}
                    />
                </svg>
            ) : (
                <XCircle size={16} className="shrink-0 text-destructive" />
            )}
            <div className="flex-1">
                <p className="font-mono text-xs text-foreground">
                    {correct
                        ? 'Correct! SM-2 interval extended.'
                        : `Incorrect. Correct answer: ${quiz.correct_answer}`}
                </p>
            </div>
            {action}
        </m.div>
    )
}
