import { ChatInterface } from '@/components/ask/ChatInterface'
import { askQuestion } from '@/services/api'

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
          <ChatInterface onSend={askQuestion} />
        </div>
      </div>
    </div>
  )
}
