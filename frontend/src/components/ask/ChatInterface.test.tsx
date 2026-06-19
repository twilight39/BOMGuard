import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { ChatInterface } from './ChatInterface'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  sent: string[] = []

  constructor() {
    MockWebSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    // no-op for tests
  }
}

const fetchMeMock = vi.fn()
const fetchChatThreadsMock = vi.fn()
const fetchChatMessagesMock = vi.fn()

vi.mock('@/services/api', async () => {
  return {
    fetchMe: () => fetchMeMock(),
    fetchChatThreads: () => fetchChatThreadsMock(),
    fetchChatMessages: (id: number) => fetchChatMessagesMock(id),
    createChatThread: vi.fn(),
    syncAnonymousThread: vi.fn(),
  }
})

describe('ChatInterface', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
    fetchMeMock.mockReset()
    fetchChatThreadsMock.mockReset()
    fetchChatMessagesMock.mockReset()
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends a message over WebSocket', async () => {
    fetchMeMock.mockResolvedValue(null)

    render(<ChatInterface wsUrl="ws://localhost:8000/api/ask/ws" />)

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1)
    })

    act(() => {
      MockWebSocket.instances[0].onopen?.()
    })

    const textarea = screen.getByPlaceholderText(/Ask about chemical regulations/i)
    fireEvent.change(textarea, { target: { value: 'Hello' } })
    fireEvent.click(screen.getByRole('button', { name: /Send/i }))

    await waitFor(() => {
      expect(MockWebSocket.instances[0].sent.length).toBe(1)
    })
    expect(MockWebSocket.instances[0].sent[0]).toContain('Hello')
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('renders markdown in assistant messages', async () => {
    fetchMeMock.mockResolvedValue(null)

    render(<ChatInterface wsUrl="ws://localhost:8000/api/ask/ws" />)

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1)
    })

    act(() => {
      MockWebSocket.instances[0].onopen?.()
    })

    act(() => {
      MockWebSocket.instances[0].onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({ type: 'token', content: '# Heading\n\n**bold**' }),
        })
      )
    })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Heading/i })).toBeInTheDocument()
    })
    expect(screen.getByText('bold')).toBeInTheDocument()
  })

  it('loads the first thread for authenticated users', async () => {
    fetchMeMock.mockResolvedValue({ id: 'user-1', email: 'test@example.com' })
    fetchChatThreadsMock.mockResolvedValue([{ id: 7, title: 'Thread 7' }])
    fetchChatMessagesMock.mockResolvedValue([
      { id: 1, role: 'user', content: 'Previous question', createdAt: '2026-01-01' },
    ])

    render(<ChatInterface wsUrl="ws://localhost:8000/api/ask/ws" />)

    await waitFor(() => {
      expect(fetchChatThreadsMock).toHaveBeenCalled()
    })
    await waitFor(() => {
      expect(fetchChatMessagesMock).toHaveBeenCalledWith(7)
    })
    await waitFor(() => {
      expect(screen.getByText('Previous question')).toBeInTheDocument()
    })
  })
})
