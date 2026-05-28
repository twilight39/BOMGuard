import { createFileRoute } from '@tanstack/react-router'
import { AskPage } from '@/pages/AskPage'

export const Route = createFileRoute('/ask')({
  component: AskPage,
})
