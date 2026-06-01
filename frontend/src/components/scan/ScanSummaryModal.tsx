import { Button } from '@/components/ui/button'

interface ScanSummary {
  bomId: number
  name: string
  status: string
  hits: number
}

interface ScanSummaryModalProps {
  open: boolean
  summaries: ScanSummary[]
  onClose: () => void
  onViewResult: (bomId: number) => void
}

export function ScanSummaryModal({ open, summaries, onClose, onViewResult }: ScanSummaryModalProps) {
  if (!open || summaries.length === 0) return null

  const totalHits = summaries.reduce((sum, s) => sum + s.hits, 0)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-lg border bg-card shadow-lg p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Scan Complete</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground text-lg leading-none px-2 py-1 rounded-md hover:bg-muted transition-colors cursor-pointer"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <p className="text-sm text-muted-foreground">
          Scanned {summaries.length} BOM{summaries.length !== 1 ? 's' : ''} · {totalHits} total hit{totalHits !== 1 ? 's' : ''}
        </p>

        <div className="rounded-lg border divide-y">
          {summaries.map((s) => (
            <div key={s.bomId} className="flex items-center justify-between px-4 py-3">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{s.name}</p>
                <p className="text-xs text-muted-foreground capitalize">
                  {s.status} · {s.hits} hit{s.hits !== 1 ? 's' : ''}
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={() => onViewResult(s.bomId)}>
                View
              </Button>
            </div>
          ))}
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button onClick={() => onViewResult(summaries[0].bomId)}>
            View First Result
          </Button>
        </div>
      </div>
    </div>
  )
}
