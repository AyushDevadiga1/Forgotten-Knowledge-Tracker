import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from '../badge'

describe('Badge', () => {
    it('renders children text', () => {
        render(<Badge>Active</Badge>)
        expect(screen.getByText('Active')).toBeInTheDocument()
    })
})
