import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Merge Tailwind classes with conflict resolution — used by all ui primitives. */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}
