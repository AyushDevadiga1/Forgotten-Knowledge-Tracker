import { type ReactNode } from 'react'
import type { QuizQuestion } from '@/api'
import { useQuizAnswer } from '@/hooks/useQuizAnswer'
import { cn } from '@/lib/utils'
import QuizOption from './QuizOption'
import QuizResultBanner from './QuizResultBanner'

interface QuizOptionListProps {
    quiz: QuizQuestion
    /** Fires once per answered question with whether the pick was correct. */
    onAnswer?: (correct: boolean) => void
    /** Trailing action shown inside the result banner (Next / Close). */
    action?: ReactNode
}

/** The single shared place that wires the quiz-answer interaction (M-3
 * useQuizAnswer hook) to animated option rendering + the result banner. Both
 * QuizPage and MicroQuizModal render this — no duplicated behaviour. */
export default function QuizOptionList({ quiz, onAnswer, action }: QuizOptionListProps) {
    const { selected, answerState, handleSelect, optionClass } = useQuizAnswer()

    const onSelect = async (option: string) => {
        const correct = await handleSelect(quiz, option)
        if (correct !== undefined) onAnswer?.(correct)
    }

    return (
        <>
            <div id="quiz-options" className="space-y-2">
                {(quiz.options ?? []).map((opt, i) => (
                    <QuizOption
                        key={i}
                        index={i}
                        option={opt}
                        quiz={quiz}
                        selected={selected}
                        answerState={answerState}
                        className={cn(optionClass(quiz, opt), 'py-3')}
                        onSelect={onSelect}
                    />
                ))}
            </div>
            <QuizResultBanner quiz={quiz} answerState={answerState} action={action} />
        </>
    )
}
