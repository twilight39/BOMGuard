import { createFileRoute } from '@tanstack/react-router'
import { BomDetailPage } from '@/pages/BomDetailPage'

export const Route = createFileRoute('/boms/$bomId')({
  component: BomDetailPage,
})
