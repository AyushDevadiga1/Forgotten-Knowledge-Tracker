import { useState } from 'react'
import { m } from 'motion/react'
import { Eye } from 'lucide-react'
import type { QuizQuestion } from '@/api'
import { easeOut } from '@/lib/animation'
import { cn } from '@/lib/utils'

interface FlashcardViewProps {
    quiz: QuizQuestion
    onAnswer: (correct: boolean) => void
    action: React.ReactNode
}

export default function FlashcardView({ quiz, onAnswer, action }: FlashcardViewProps) {
    const [flipped, setFlipped] = useState(false)
    const [feedback, setFeedback] = useState<'correct' | 'wrong' | null>(null)

    return (
        <div className="space-y-4">
            <m.div
                className={cn(
                    "relative flex min-h-[200px] cursor-pointer items-center justify-center border bg-background p-8 text-center transition-colors",
                    feedback === 'correct' ? 'border-primary' : feedback === 'wrong' ? 'border-red-500' : 'border-border'
                )}
                animate={feedback === 'wrong' ? { x: [0, -6, 6, -4, 4, 0] } : {}}
                transition={{ duration: 0.4, ease: easeOut }}
                onClick={() => !flipped && setFlipped(true)}
                whileHover={!flipped ? { scale: 1.01 } : undefined}
                whileTap={!flipped ? { scale: 0.99 } : undefined}
            >
                {!flipped ? (
                    <m.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.2 }}
                    >
                        <p className="font-mono text-2xl font-bold text-foreground">{quiz.question}</p>
                        <p className="mt-3 flex items-center justify-center gap-1.5 text-[10px] uppercase tracking-widest text-muted-foreground">
                            <Eye size={11} /> Click to reveal answer
                        </p>
                    </m.div>
                ) : (
                    <m.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.3, ease: easeOut }}
                    >
                        <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                            Answer
                        </p>
                        <p className="font-sans text-sm leading-relaxed text-foreground">
                            {quiz.answer || 'No answer available'}
                        </p>
                    </m.div>
                )}
            </m.div>

            {flipped && (
                <m.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: 0.1 }}
                    className="flex items-center justify-between"
                >
                    <div className="flex gap-2">
                        <button
                            onClick={() => { setFeedback('correct'); setTimeout(() => { onAnswer(true); setFlipped(false); setFeedback(null) }, 500) }}
                            className="border border-primary/40 bg-primary/10 px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-primary transition-colors hover:bg-primary/20"
                        >
                            Got it
                        </button>
                        <button
                            onClick={() => { setFeedback('wrong'); setTimeout(() => { onAnswer(false); setFlipped(false); setFeedback(null) }, 500) }}
                            className="border border-red-500/40 bg-red-500/10 px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-red-500 transition-colors hover:bg-red-500/20"
                        >
                            Missed it
                        </button>
                    </div>
                    {action}
                </m.div>
            )}
        </div>
    )
}
