import { AiAssistantLayout } from '@/components/ai-assistant/AiAssistantLayout'
import { Route } from '@/routes/ask'

export function AskPage() {
  const { bomId } = Route.useSearch()
  return <AiAssistantLayout bomId={bomId} />
}
