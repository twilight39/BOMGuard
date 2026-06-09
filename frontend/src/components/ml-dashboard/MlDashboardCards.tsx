import * as React from 'react'
import { Button } from '@/components/ui/button'
import {
  fetchRegulations,
  fetchModelPerformance,
  fetchModelDrift,
  retrainModel,
  type Regulation,
} from '@/services/api'

function regulationLabel(id: string): string {
  return id
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export function MlDashboardCards() {
  const [regulations, setRegulations] = React.useState<Regulation[]>([])
  const [loading, setLoading] = React.useState(true)
  const [retraining, setRetraining] = React.useState<Set<string>>(new Set())

  React.useEffect(() => {
    let cancelled = false
    fetchRegulations()
      .then((data) => {
        if (!cancelled) setRegulations(data)
      })
      .catch(() => {
        if (!cancelled) setRegulations([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleRetrain = async (id: string) => {
    setRetraining((prev) => new Set(prev).add(id))
    try {
      await retrainModel(id)
      alert(`Retraining queued for ${regulationLabel(id)}`)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Retrain failed')
    } finally {
      setRetraining((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-bold">ML Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Model performance, drift monitoring, and retraining controls.
        </p>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Loading regulations…</p>}

      {!loading && regulations.length === 0 && (
        <p className="text-sm text-muted-foreground">No regulations found.</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {regulations.map((reg) => (
          <RegulationModelCard
            key={reg.id}
            regulation={reg}
            retraining={retraining.has(reg.id)}
            onRetrain={() => handleRetrain(reg.id)}
          />
        ))}
      </div>
    </div>
  )
}

interface RegulationModelCardProps {
  regulation: Regulation
  retraining: boolean
  onRetrain: () => void
}

function RegulationModelCard({ regulation, retraining, onRetrain }: RegulationModelCardProps) {
  const [performance, setPerformance] = React.useState<Record<string, number> | null>(null)
  const [drift, setDrift] = React.useState<boolean | null>(null)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    let cancelled = false
    Promise.all([
      fetchModelPerformance(regulation.id).catch(() => null),
      fetchModelDrift(regulation.id).catch(() => null),
    ])
      .then(([perf, driftData]) => {
        if (cancelled) return
        setPerformance(perf?.metrics || null)
        setDrift(driftData?.driftDetected ?? null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [regulation.id])

  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-sm">{regulation.name}</h3>
          <p className="text-xs text-muted-foreground font-mono">{regulation.id}</p>
        </div>
        {regulation.mlEnabled ? (
          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
            ML enabled
          </span>
        ) : (
          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs bg-muted text-muted-foreground">
            Rule-based
          </span>
        )}
      </div>

      {loading ? (
        <p className="text-xs text-muted-foreground">Loading metrics…</p>
      ) : (
        <div className="space-y-1">
          {performance && Object.keys(performance).length > 0 ? (
            Object.entries(performance).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{key}</span>
                <span className="font-medium tabular-nums">{Number(value).toFixed(3)}</span>
              </div>
            ))
          ) : (
            <p className="text-xs text-muted-foreground">No performance data available.</p>
          )}

          {drift !== null && (
            <div className="flex items-center justify-between text-xs pt-2 border-t">
              <span className="text-muted-foreground">Drift</span>
              <span
                className={[
                  'font-medium',
                  drift ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400',
                ].join(' ')}
              >
                {drift ? 'Detected' : 'None'}
              </span>
            </div>
          )}
        </div>
      )}

      {regulation.mlEnabled && (
        <Button
          size="sm"
          variant="outline"
          className="w-full"
          onClick={onRetrain}
          disabled={retraining}
        >
          {retraining ? 'Retraining…' : 'Retrain model'}
        </Button>
      )}
    </div>
  )
}
