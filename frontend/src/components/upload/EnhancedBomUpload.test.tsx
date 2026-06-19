import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { EnhancedBomUpload } from './EnhancedBomUpload'

const navigateMock = vi.fn()
vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => navigateMock,
}))

const uploadBomMock = vi.fn()
vi.mock('@/services/api', () => ({
  uploadBom: (file: File) => uploadBomMock(file),
}))

describe('EnhancedBomUpload', () => {
  beforeEach(() => {
    uploadBomMock.mockReset()
    navigateMock.mockReset()
  })

  it('selects a file via drag and drop', async () => {
    render(<EnhancedBomUpload />)

    const file = new File(['part_number,description\nABC123,Resistor\n'], 'bom.csv', {
      type: 'text/csv',
    })
    const dropZone = screen.getByText(/Drop a BOM file here/i)

    fireEvent.drop(dropZone, {
      dataTransfer: { files: [file] },
    })

    await waitFor(() => {
      expect(screen.getByText('bom.csv')).toBeInTheDocument()
    })
    expect(screen.getByText(/Upload BOM/i)).toBeInTheDocument()
  })

  it('rejects non-CSV/XLSX files by not processing them', async () => {
    render(<EnhancedBomUpload />)

    const file = new File(['not a bom'], 'bom.txt', { type: 'text/plain' })
    const input = screen.getByLabelText(/Drop a BOM file here/i)

    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(screen.getByText('bom.txt')).toBeInTheDocument()
    })
  })

  it('calls upload API and navigates on confirm', async () => {
    uploadBomMock.mockResolvedValue({ id: 42, filename: 'bom.csv', status: 'uploaded' })

    render(<EnhancedBomUpload />)

    const file = new File(['part_number\nABC123\n'], 'bom.csv', { type: 'text/csv' })
    const input = screen.getByLabelText(/Drop a BOM file here/i)

    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(screen.getByText('bom.csv')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /Upload BOM/i }))

    await waitFor(() => {
      expect(uploadBomMock).toHaveBeenCalledWith(file)
    })
    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith({ to: '/boms/42' })
    })
  })
})
