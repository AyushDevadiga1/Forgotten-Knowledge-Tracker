import { useEffect, useRef, useState } from 'react'
import { useMotionValue, useReducedMotion, useSpring } from 'motion/react'

interface AnimatedNumberProps {
    value: number
    format?: (v: number) => string
    className?: string
}

/** Bklit-style animated counter — counts up from 0 on mount and on every
 * value update instead of snapping. Respects prefers-reduced-motion. */
export default function AnimatedNumber({ value, format, className }: AnimatedNumberProps) {
    const reduced = useReducedMotion()
    const mv = useMotionValue(0)
    const springValue = useSpring(mv, { stiffness: 80, damping: 26, mass: 1 })
    const [display, setDisplay] = useState(() => (format ? format(0) : '0'))
    const formatRef = useRef(format)
    formatRef.current = format

    useEffect(() => {
        if (reduced) {
            setDisplay(formatRef.current ? formatRef.current(value) : String(Math.round(value)))
            return
        }
        const unsub = springValue.on('change', (v) => {
            setDisplay(formatRef.current ? formatRef.current(v) : String(Math.round(v)))
        })
        mv.set(0)
        mv.set(value)
        return unsub
    }, [reduced, value, mv, springValue])

    return <span className={className}>{display}</span>
}
