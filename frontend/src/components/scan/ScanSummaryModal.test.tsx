import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ScanSummaryModal } from './ScanSummaryModal'

const summaries = [
  { bomId: 1, name: 'BOM A', status: 'completed', hits: 3 },
  { bomId: 2, name: 'BOM B', status: 'completed', hits: 0 },
]

describe('ScanSummaryModal', () => {
  it('renders status and hit counts', () => {
    render(
      <ScanSummaryModal
        open
        summaries={summaries}
        onClose={vi.fn()}
        onViewResult={vi.fn()}
      />
    )

    expect(screen.getByText('Scan Complete')).toBeInTheDocument()
    expect(screen.getByText('BOM A')).toBeInTheDocument()
    expect(screen.getByText(/3 hits/i)).toBeInTheDocument()
    expect(screen.getByText('BOM B')).toBeInTheDocument()
    expect(screen.getByText(/0 hits/i)).toBeInTheDocument()
    expect(screen.getByText(/2 BOMs · 3 total hits/i)).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn()
    render(
      <ScanSummaryModal open summaries={summaries} onClose={onClose} onViewResult={vi.fn()} />
    )

    fireEvent.click(screen.getByLabelText(/Close/i))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onViewResult when View button is clicked', () => {
    const onViewResult = vi.fn()
    render(
      <ScanSummaryModal open summaries={summaries} onClose={vi.fn()} onViewResult={onViewResult} />
    )

    const viewButtons = screen.getAllByRole('button', { name: /View/i })
    fireEvent.click(viewButtons[0])
    expect(onViewResult).toHaveBeenCalledWith(1)
  })

  it('returns null when not open', () => {
    const { container } = render(
      <ScanSummaryModal
        open={false}
        summaries={summaries}
        onClose={vi.fn()}
        onViewResult={vi.fn()}
      />
    )

    expect(container.firstChild).toBeNull()
  })
})
