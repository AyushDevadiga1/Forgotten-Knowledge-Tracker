import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import EmptyState from '../EmptyState'

describe('EmptyState', () => {
    it('renders the label', () => {
        render(<EmptyState label="No data yet" />)
        expect(screen.getByText(/No data yet/)).toBeInTheDocument()
    })

    it('renders the hint when provided', () => {
        render(<EmptyState label="Empty" hint="Add some items first" />)
        expect(screen.getByText(/Add some items first/)).toBeInTheDocument()
    })

    it('does not render hint when omitted', () => {
        render(<EmptyState label="Nothing here" />)
        expect(screen.queryByText(/Add some/)).not.toBeInTheDocument()
    })
})
