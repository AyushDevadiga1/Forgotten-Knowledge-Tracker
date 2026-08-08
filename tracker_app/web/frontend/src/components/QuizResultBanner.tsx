import { CheckCircle, XCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import type { QuizQuestion } from '../api'
import type { AnswerState } from '../hooks/useQuizAnswer'

// Shared quiz result banner (M-3). Previously the same JSX lived in
// QuizPage.tsx and MicroQuizModal.tsx; the only difference is the trailing
// action button, which callers pass as `action`. Renders nothing while idle.
export default function QuizResultBanner({ quiz, answerState, action }: {
    quiz: QuizQuestion
    answerState: AnswerState
    action?: ReactNode
}) {
    if (answerState === 'idle') return null

    const correct = answerState === 'correct'
    return (
        <div className={`mt-5 p-3 border flex items-center gap-3 ${
            correct ? 'border-fkt-accent bg-fkt-accent/5' : 'border-[#EF4444] bg-[#EF4444]/5'
        }`}>
            {correct
                ? <CheckCircle size={16} className="text-fkt-accent shrink-0" />
                : <XCircle size={16} className="text-[#EF4444] shrink-0" />
            }
            <div className="flex-1">
                <p className="text-xs font-mono text-fkt-text-primary">
                    {correct
                        ? 'Correct! SM-2 interval extended.'
                        : `Incorrect. Correct answer: ${quiz.correct_answer}`}
                </p>
            </div>
            {action}
        </div>
    )
}
