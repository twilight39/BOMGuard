import { createFileRoute } from '@tanstack/react-router'
import { BomsPage } from '@/pages/BomsPage'

export const Route = createFileRoute('/boms/')({
  component: BomsPage,
})
