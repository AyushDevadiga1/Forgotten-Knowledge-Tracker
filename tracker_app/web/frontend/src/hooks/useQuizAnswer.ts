import { useState } from 'react'
import { api, QuizQuestion } from '../api'

export type AnswerState = 'idle' | 'correct' | 'wrong'

// Shared quiz-answer interaction logic (M-3). Previously duplicated
// character-for-character in QuizPage.tsx and MicroQuizModal.tsx:
// the guard, the selected/answerState pair, the SM-2 answer submission,
// and the option styling. Returns true/false for whether the answer was
// correct, or undefined if the interaction was ignored (already answered).
export function useQuizAnswer() {
    const [selected, setSelected] = useState<string | null>(null)
    const [answerState, setAnswerState] = useState<AnswerState>('idle')

    const reset = () => {
        setSelected(null)
        setAnswerState('idle')
    }

    const handleSelect = async (quiz: QuizQuestion, option: string): Promise<boolean | undefined> => {
        if (answerState !== 'idle' || !quiz) return undefined
        setSelected(option)
        const correct = option === quiz.correct_answer
        setAnswerState(correct ? 'correct' : 'wrong')
        try {
            await api.submitQuizAnswer(quiz.concept, correct)
        } catch {
            // fire-and-forget — don't block the UI on a failed SM-2 write
        }
        return correct
    }

    const optionClass = (quiz: QuizQuestion | null, option: string) => {
        const base = 'w-full text-left px-4 py-3 border font-mono text-xs transition-all duration-200 '
        if (answerState === 'idle')
            return base + 'border-fkt-elevated text-fkt-text-primary hover:border-fkt-accent hover:text-fkt-accent bg-fkt-base cursor-pointer'
        if (option === quiz?.correct_answer)
            return base + 'border-fkt-accent text-fkt-accent bg-fkt-accent/5 cursor-default'

        if (option === selected && answerState === 'wrong')
            return base + 'border-[#EF4444] text-[#EF4444] bg-[#EF4444]/5 cursor-default'
        return base + 'border-fkt-elevated text-fkt-text-dim cursor-default opacity-50'
    }

    return { selected, answerState, reset, handleSelect, optionClass }
}
