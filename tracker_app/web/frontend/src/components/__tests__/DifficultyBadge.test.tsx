import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import DifficultyBadge from '../DifficultyBadge'

describe('DifficultyBadge', () => {
    it('renders Easy for easy difficulty', () => {
        render(<DifficultyBadge difficulty="easy" />)
        expect(screen.getByText('Easy')).toBeInTheDocument()
    })

    it('renders Medium for medium difficulty', () => {
        render(<DifficultyBadge difficulty="medium" />)
        expect(screen.getByText('Medium')).toBeInTheDocument()
    })

    it('renders Hard for hard difficulty', () => {
        render(<DifficultyBadge difficulty="hard" />)
        expect(screen.getByText('Hard')).toBeInTheDocument()
    })

    it('defaults to Medium for unknown difficulty', () => {
        render(<DifficultyBadge difficulty="unknown" />)
        expect(screen.getByText('Medium')).toBeInTheDocument()
    })

    it('defaults to Medium when no difficulty is given', () => {
        render(<DifficultyBadge />)
        expect(screen.getByText('Medium')).toBeInTheDocument()
    })
})
