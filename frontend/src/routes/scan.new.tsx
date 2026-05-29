import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/scan/new')({
  component: () => (
    <div className="space-y-4">
      <h1 className="text-2xl font-heading font-bold">New Scan</h1>
      <div className="rounded-lg border bg-card p-8 text-center">
        <p className="text-muted-foreground text-sm">Select a BOM to scan.</p>
      </div>
    </div>
  ),
})
