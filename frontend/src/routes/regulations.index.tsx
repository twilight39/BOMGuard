import { createFileRoute } from '@tanstack/react-router'
import { RegulationsPage } from '@/pages/RegulationsPage'

export const Route = createFileRoute('/regulations/')({
  component: RegulationsPage,
})
