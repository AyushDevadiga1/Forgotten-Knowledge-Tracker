import { describe, it, expect } from 'vitest'
import { cn } from '../utils'

describe('cn', () => {
    it('merges class names', () => {
        const result = cn('text-red-500', 'text-blue-500')
        expect(result).toBe('text-blue-500')
    })

    it('handles conditional classes', () => {
        const result = cn('base', false && 'hidden', 'extra')
        expect(result).toContain('base')
        expect(result).toContain('extra')
        expect(result).not.toContain('hidden')
    })

    it('returns empty string for no args', () => {
        expect(cn()).toBe('')
    })
})
