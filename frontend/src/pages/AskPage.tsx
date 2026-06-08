import { ChatInterface } from '@/components/ask/ChatInterface'

const API_BASE = import.meta.env.VITE_API_URL || ''

function getWsUrl(apiBase: string): string {
  if (apiBase) {
    const url = apiBase
      .replace(/^http:\/\//, 'ws://')
      .replace(/^https:\/\//, 'wss://')
    return `${url}/api/ask/ws`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/ask/ws`
}

export function AskPage() {
  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col">
      <div className="px-6 pt-6 pb-2">
        <h1 className="text-2xl font-heading font-bold">Regulatory AI Assistant</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Ask me anything about chemical regulations.
        </p>
      </div>
      <div className="flex-1 min-h-0 px-6 pb-6">
        <div className="h-full rounded-xl border bg-card overflow-hidden">
          <ChatInterface wsUrl={getWsUrl(API_BASE)} />
        </div>
      </div>
    </div>
  )
}
