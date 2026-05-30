import * as React from 'react'
import { Button } from '@/components/ui/button'

export interface Source {
  id: number
  substance_id: number | null
  regulation_id: string | null
  summary_text: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
}

interface ChatInterfaceProps {
  onSend: (question: string) => Promise<{ answer: string; sources: Source[] }>
}

export function ChatInterface({ onSend }: ChatInterfaceProps) {
  const [messages, setMessages] = React.useState<Message[]>([])
  const [input, setInput] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const bottomRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async () => {
    const question = input.trim()
    if (!question || loading) return

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setLoading(true)

    try {
      const result = await onSend(question)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: result.answer, sources: result.sources },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, something went wrong. Please try again.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground text-sm py-12">
            Ask a question about chemical regulations to get started.
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-foreground'
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {msg.sources.map((source) => (
                    <span
                      key={source.id}
                      className="inline-flex items-center rounded-full bg-background/80 px-2 py-0.5 text-xs text-muted-foreground border"
                      title={source.summary_text}
                    >
                      {source.regulation_id ?? `Substance ${source.substance_id}`}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-xl px-4 py-3 text-sm text-muted-foreground animate-pulse">
              Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t p-4 bg-card">
        <div className="flex gap-2 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about chemical regulations…"
            rows={1}
            className="flex-1 resize-none rounded-lg border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring min-h-[40px] max-h-[120px]"
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            size="default"
          >
            Send
          </Button>
        </div>
      </div>
    </div>
  )
}
