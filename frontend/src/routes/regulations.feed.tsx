import { createFileRoute } from '@tanstack/react-router'
import { RegulatoryFeedPage } from '@/pages/RegulatoryFeedPage'

export const Route = createFileRoute('/regulations/feed')({
  component: RegulatoryFeedPage,
})
