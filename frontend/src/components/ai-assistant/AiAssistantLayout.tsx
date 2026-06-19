import * as React from 'react'
import { ChatInterface } from '@/components/ask/ChatInterface'
import { fetchChatThreads, type ChatThread } from '@/services/api'

function getWsUrl(): string {
  const apiBase = import.meta.env.VITE_API_URL || ''
  if (apiBase) {
    const url = apiBase
      .replace(/^http:\/\//, 'ws://')
      .replace(/^https:\/\//, 'wss://')
    return `${url}/api/ask/ws`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/ask/ws`
}

export function AiAssistantLayout() {
  const [threads, setThreads] = React.useState<ChatThread[]>([])
  const [loading, setLoading] = React.useState(true)
  const [selectedThreadId, setSelectedThreadId] = React.useState<number | undefined>()

  React.useEffect(() => {
    let cancelled = false
    fetchChatThreads()
      .then((data) => {
        if (cancelled) return
        setThreads(data)
        if (data.length > 0) {
          setSelectedThreadId(data[0].id)
        }
      })
      .catch(() => {
        if (!cancelled) setThreads([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="h-[calc(100vh-3.5rem)] flex">
      {/* Thread sidebar */}
      <aside className="w-64 border-r bg-card flex flex-col hidden md:flex">
        <div className="h-14 flex items-center px-4 border-b">
          <h2 className="font-semibold text-sm">Threads</h2>
        </div>
        <div className="flex-1 overflow-auto p-2">
          {loading && <p className="text-xs text-muted-foreground px-2 py-1">Loading…</p>}
          {!loading && threads.length === 0 && (
            <p className="text-xs text-muted-foreground px-2 py-1">No threads yet.</p>
          )}
          {threads.map((thread) => (
            <button
              key={thread.id}
              onClick={() => setSelectedThreadId(thread.id)}
              className={[
                'w-full text-left rounded-md px-2 py-1.5 text-sm truncate transition-colors',
                selectedThreadId === thread.id
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground',
              ].join(' ')}
            >
              {thread.title || `Thread ${thread.id}`}
            </button>
          ))}
        </div>
      </aside>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="px-6 pt-6 pb-2">
          <h1 className="text-2xl font-heading font-bold">Regulatory AI Assistant</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Ask me anything about chemical regulations.
          </p>
        </div>
        <div className="flex-1 min-h-0 px-6 pb-6">
          <div className="h-full rounded-xl border bg-card overflow-hidden">
            <ChatInterface wsUrl={getWsUrl()} />
          </div>
        </div>
      </div>
    </div>
  )
}
