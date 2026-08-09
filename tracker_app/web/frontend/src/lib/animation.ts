import type { Transition, Variants } from 'motion/react'

/** Standard spring — the only spring FKT uses for layout/presence motion. */
export const spring: Transition = { type: 'spring', stiffness: 380, damping: 32, mass: 0.8 }

/** Signature FKT easing — fast-in, slow-out, terminal-grade. */
export const easeOut: [number, number, number, number] = [0.16, 1, 0.3, 1]

/** Shared page-level route transition (fade + slight slide). */
export const pageVariants: Variants = {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -8 },
}

/** Default transition applied to pageVariants. */
export const pageTransition: Transition = { duration: 0.18, ease: easeOut }
