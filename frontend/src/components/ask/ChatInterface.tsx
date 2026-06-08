import * as React from 'react'
import ReactMarkdown from 'react-markdown'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  fetchMe,
  fetchChatThreads,
  fetchChatMessages,
  createChatThread,
  syncAnonymousThread,
  type ChatMessage as DbChatMessage,
} from '@/services/api'

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
  wsUrl: string
}

const STARTER_QUESTIONS = [
  'How can you help?',
  'What regulations are in the system?',
  'How can I add regulations?',
]

const LS_KEY = 'bomguard-chat-history'
const LS_SYNCED_KEY = 'bomguard-chat-synced'

function formatRegulationId(id: string | null): string {
  if (!id) return ''
  return id
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

function sourceLabel(source: Source): string {
  if (source.regulation_id) {
    return formatRegulationId(source.regulation_id)
  }
  const text = source.summary_text
  if (text && text.length > 40) {
    return text.slice(0, 40) + '…'
  }
  return text || 'Source'
}

function followUpQuestion(source: Source): string {
  if (source.regulation_id) {
    return `Tell me more about ${formatRegulationId(source.regulation_id)}`
  }
  return 'Tell me more about this substance'
}

function dbToLocal(dbMsgs: DbChatMessage[]): Message[] {
  return dbMsgs.map((m) => ({
    role: m.role,
    content: m.content,
    sources: (m.sources as Source[] | undefined) ?? undefined,
  }))
}

function loadLocal(): Message[] {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (raw) return JSON.parse(raw)
  } catch {
    // ignore
  }
  return []
}

function saveLocal(messages: Message[]) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(messages))
  } catch {
    // ignore
  }
}

function clearLocal() {
  localStorage.removeItem(LS_KEY)
}

function wasSynced(): boolean {
  return localStorage.getItem(LS_SYNCED_KEY) === '1'
}

function markSynced() {
  localStorage.setItem(LS_SYNCED_KEY, '1')
}

export function ChatInterface({ wsUrl }: ChatInterfaceProps) {
  const [messages, setMessages] = React.useState<Message[]>([])
  const [input, setInput] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [connected, setConnected] = React.useState(false)
  const [threadId, setThreadId] = React.useState<number | undefined>()
  const [authUserId, setAuthUserId] = React.useState<string | null>(null)
  const [showSyncBanner, setShowSyncBanner] = React.useState(false)
  const bottomRef = React.useRef<HTMLDivElement>(null)
  const wsRef = React.useRef<WebSocket | null>(null)

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // On mount: detect auth, load single thread or localStorage
  React.useEffect(() => {
    let cancelled = false

    async function init() {
      const user = await fetchMe()
      if (cancelled) return

      if (user) {
        setAuthUserId(user.id)
        const threads = await fetchChatThreads()
        if (cancelled) return

        if (threads.length > 0) {
          // Load the single persistent thread
          const singleThread = threads[0]
          setThreadId(singleThread.id)
          const dbMsgs = await fetchChatMessages(singleThread.id)
          if (cancelled) return
          setMessages(dbToLocal(dbMsgs))
        } else {
          // No thread yet — check for anonymous messages to sync
          const localMsgs = loadLocal()
          if (localMsgs.length > 0 && !wasSynced()) {
            setShowSyncBanner(true)
          }
        }
      } else {
        // Anonymous: load from localStorage
        setMessages(loadLocal())
      }
    }

    init()
    return () => {
      cancelled = true
    }
  }, [])

  // Persist anonymous messages to localStorage
  React.useEffect(() => {
    if (!authUserId && messages.length > 0) {
      saveLocal(messages)
    }
  }, [messages, authUserId])

  // WebSocket connection
  React.useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => setConnected(false)
      ws.onerror = () => setConnected(false)

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)

        if (data.type === 'thread') {
          setThreadId(data.thread_id)
        } else if (data.type === 'token') {
          setMessages((prev) => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              const updated = [...prev]
              updated[updated.length - 1] = {
                ...last,
                content: last.content + data.content,
              }
              return updated
            }
            return [...prev, { role: 'assistant', content: data.content }]
          })
        } else if (data.type === 'sources') {
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last && last.role === 'assistant') {
              updated[updated.length - 1] = {
                ...last,
                sources: data.sources,
              }
            }
            return updated
          })
        } else if (data.type === 'done') {
          setLoading(false)
        } else if (data.type === 'error') {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: `Error: ${data.message}`,
            },
          ])
          setLoading(false)
        }
      }
    }

    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [wsUrl])

  const sendQuestion = React.useCallback(
    (question: string) => {
      if (!question || loading || !connected) return

      setInput('')
      setMessages((prev) => [...prev, { role: 'user', content: question }])
      setLoading(true)

      wsRef.current?.send(
        JSON.stringify({ question, thread_id: threadId ?? null })
      )
    },
    [loading, connected, threadId]
  )

  const handleSend = () => {
    sendQuestion(input.trim())
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClear = () => {
    setMessages([])
    clearLocal()
    setThreadId(undefined)
  }

  const handleSync = React.useCallback(async () => {
    if (!authUserId) return
    const localMsgs = loadLocal()
    if (localMsgs.length === 0) return

    try {
      const thread = await createChatThread(localMsgs[0]?.content.slice(0, 50))
      await syncAnonymousThread(
        thread.id,
        localMsgs.map((m) => ({
          role: m.role,
          content: m.content,
          sources: m.sources,
        }))
      )
      markSynced()
      clearLocal()
      setShowSyncBanner(false)
      setThreadId(thread.id)
      setMessages(dbToLocal(await fetchChatMessages(thread.id)))
    } catch {
      // ignore
    }
  }, [authUserId])

  const msgCount = messages.length
  const showWarning = msgCount >= 40 && msgCount < 50
  const showLimit = msgCount >= 50

  return (
    <TooltipProvider>
      <div className="flex flex-col h-full">
        <div className="flex-1 overflow-y-auto space-y-4 p-4">
          {messages.length === 0 && !showSyncBanner && (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <p className="text-muted-foreground text-sm">
                Ask a question about chemical regulations to get started.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {STARTER_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => sendQuestion(q)}
                    className="rounded-full border bg-card px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {showSyncBanner && (
            <div className="rounded-md border bg-card px-4 py-3 flex items-center justify-between gap-3">
              <p className="text-sm">
                You have anonymous chats. Sync them to your account?
              </p>
              <div className="flex gap-2">
                <Button size="sm" onClick={handleSync}>
                  Sync
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setShowSyncBanner(false)}>
                  Dismiss
                </Button>
              </div>
            </div>
          )}

          {showWarning && (
            <div className="text-center text-xs text-amber-600 bg-amber-50 rounded-md px-3 py-1.5">
              Thread limit approaching ({msgCount}/50) — start a new chat soon.
            </div>
          )}
          {showLimit && (
            <div className="text-center text-xs text-destructive bg-destructive/10 rounded-md px-3 py-1.5">
              Thread limit reached (50 messages). Clear chat to continue.
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
                <div
                  className={`whitespace-pre-wrap max-w-none ${
                    msg.role === 'assistant'
                      ? 'prose prose-sm dark:prose-invert prose-headings:my-2 prose-p:my-0.5 prose-ul:my-0 prose-li:my-0'
                      : ''
                  }`}
                >
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : (
                    msg.content
                  )}
                </div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {msg.sources.map((source) => (
                      <Tooltip key={source.id}>
                        <TooltipTrigger asChild>
                          <button
                            type="button"
                            onClick={() => sendQuestion(followUpQuestion(source))}
                            className="inline-flex items-center rounded-full bg-background/80 px-2 py-0.5 text-xs text-muted-foreground border hover:bg-background cursor-pointer transition-colors"
                          >
                            {sourceLabel(source)}
                          </button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>
                            Ask about this{' '}
                            {source.regulation_id ? 'regulation' : 'substance'}
                          </p>
                        </TooltipContent>
                      </Tooltip>
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
              disabled={!input.trim() || loading || !connected || showLimit}
              size="default"
            >
              Send
            </Button>
            {messages.length > 0 && (
              <Button variant="outline" size="default" onClick={handleClear}>
                Clear
              </Button>
            )}
          </div>
          {!connected && (
            <p className="text-xs text-destructive mt-1.5">
              Not connected to the chat server.
            </p>
          )}
        </div>
      </div>
    </TooltipProvider>
  )
}
