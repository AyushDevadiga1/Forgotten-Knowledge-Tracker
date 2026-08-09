import { m } from 'motion/react'
import type { QuizQuestion } from '@/api'
import type { AnswerState } from '@/hooks/useQuizAnswer'
import { cn } from '@/lib/utils'
import { easeOut } from '@/lib/animation'

interface QuizOptionProps {
    index: number
    option: string
    quiz: QuizQuestion
    selected: string | null
    answerState: AnswerState
    /** className comes from the shared useQuizAnswer#optionClass — single source. */
    className: string
    onSelect: (option: string) => void
}

/** Animated quiz option: staggered entrance, checkmark on the correct answer,
 * shake + red flash on the wrong pick. */
export default function QuizOption({
    index,
    option,
    quiz,
    selected,
    answerState,
    className,
    onSelect,
}: QuizOptionProps) {
    const disabled = answerState !== 'idle'
    const isCorrect = option === quiz.correct_answer
    const isWrongPick = answerState === 'wrong' && option === selected

    return (
        <m.button
            type="button"
            id={`quiz-option-${index}`}
            onClick={() => onSelect(option)}
            disabled={disabled}
            className={cn(className, 'group flex items-center gap-3 text-left')}
            initial={{ opacity: 0, y: 8 }}
            animate={
                isWrongPick
                    ? { opacity: 1, y: 0, x: [0, -6, 6, -4, 4, 0] }
                    : { opacity: 1, y: 0, x: 0 }
            }
            transition={
                isWrongPick
                    ? { x: { duration: 0.4, ease: easeOut }, opacity: { duration: 0.2 } }
                    : { duration: 0.25, ease: easeOut, delay: index * 0.05 }
            }
        >
            <span className="shrink-0 text-muted-foreground">{String.fromCharCode(65 + index)}.</span>
            <span className="flex-1 text-left">{option}</span>
            {isCorrect && answerState !== 'idle' && (
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="shrink-0 text-primary">
                    <m.path
                        d="M3 7.5L5.5 10L11 4"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="square"
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: 1 }}
                        transition={{ duration: 0.3, ease: easeOut }}
                    />
                </svg>
            )}
        </m.button>
    )
}
