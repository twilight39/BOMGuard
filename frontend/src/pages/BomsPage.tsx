import { Button } from '@/components/ui/button'

export function BomsPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-bold">BOMs</h1>
        <Button>Upload BOM</Button>
      </div>
      <div className="rounded-lg border bg-card p-8 text-center">
        <p className="text-muted-foreground text-sm">No BOMs uploaded yet.</p>
        <p className="text-muted-foreground text-xs mt-1">
          Upload a CSV or XLSX to get started.
        </p>
      </div>
    </div>
  )
}
