import * as React from 'react'
import { Button } from '@/components/ui/button'
import { fetchRegulations, fetchRegulatoryFeed, type Regulation, type RegulatoryChangeItem } from '@/services/api'

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

function changeLabel(changeType: string): string {
  if (changeType === 'added') return 'Added to list'
  if (changeType === 'amended') return 'Entry amended'
  return changeType
}

function regulationLabel(id: string, regulations: Regulation[]): string {
  return regulations.find((r) => r.id === id)?.name || id
}

export function RegulatoryFeedTimeline() {
  const [regulations, setRegulations] = React.useState<Regulation[]>([])
  const [changes, setChanges] = React.useState<RegulatoryChangeItem[]>([])
  const [filterReg, setFilterReg] = React.useState('')
  const [filterSince, setFilterSince] = React.useState('')
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    let cancelled = false
    Promise.all([fetchRegulations(), fetchRegulatoryFeed(filterReg || undefined, filterSince || undefined)])
      .then(([regs, feed]) => {
        if (cancelled) return
        setRegulations(regs)
        setChanges(feed)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [filterReg, filterSince])

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-bold">Regulatory Feed</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Recent changes to tracked regulatory lists.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select
          value={filterReg}
          onChange={(e) => setFilterReg(e.target.value)}
          className="h-9 rounded-md border bg-card px-3 text-sm"
        >
          <option value="">All regulations</option>
          {regulations.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>

        <input
          type="date"
          value={filterSince}
          onChange={(e) => setFilterSince(e.target.value)}
          className="h-9 rounded-md border bg-card px-3 text-sm"
        />

        {(filterReg || filterSince) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setFilterReg('')
              setFilterSince('')
            }}
          >
            Clear filters
          </Button>
        )}
      </div>

      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {error && <p className="text-sm text-destructive">{error}</p>}

      {!loading && !error && changes.length === 0 && (
        <p className="text-sm text-muted-foreground">No changes detected in the selected period.</p>
      )}

      {!loading && !error && changes.length > 0 && (
        <div className="relative border-l pl-6 space-y-6">
          {changes.map((change) => (
            <div key={change.id} className="relative">
              <span className="absolute -left-[31px] top-1 h-3 w-3 rounded-full border-2 border-background bg-primary" />
              <div className="rounded-lg border bg-card p-4 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-primary">{changeLabel(change.changeType)}</span>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(change.detectedAt)} · {formatTime(change.detectedAt)}
                  </span>
                </div>
                <p className="text-sm font-medium">
                  {regulationLabel(change.regulationId || '', regulations)}
                </p>
                <p className="text-xs text-muted-foreground">
                  Substance ID: {change.substanceId ?? '—'}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
