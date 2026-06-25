import { createFileRoute } from '@tanstack/react-router'
import { AskPage } from '@/pages/AskPage'

export const Route = createFileRoute('/ask')({
  component: AskPage,
  validateSearch: (search: Record<string, unknown>) => {
    const bomId =
      typeof search.bomId === 'string' ? parseInt(search.bomId, 10) || undefined : undefined
    return { bomId }
  },
})
