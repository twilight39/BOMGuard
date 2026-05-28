import { createFileRoute } from '@tanstack/react-router'
import { ScanResultPage } from '@/pages/ScanResultPage'

export const Route = createFileRoute('/scan/$bomId')({
  component: ScanResultPage,
})
