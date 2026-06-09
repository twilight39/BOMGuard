import * as React from 'react'
import { Button } from '@/components/ui/button'
import { fetchShapExplanation, fetchSubstanceSummary, type ShapExplanation } from '@/services/api'

interface ScanResultDetailProps {
  casNumber: string
  regulationId?: string
  onClose: () => void
}

export function ScanResultDetail({ casNumber, regulationId, onClose }: ScanResultDetailProps) {
  const [summary, setSummary] = React.useState<{ name: string; casNumber: string | null } | null>(null)
  const [shap, setShap] = React.useState<ShapExplanation | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    let cancelled = false
    Promise.all([
      fetchSubstanceSummary(casNumber).catch(() => null),
      regulationId
        ? fetchShapExplanation(casNumber, regulationId).catch(() => null)
        : Promise.resolve(null),
    ])
      .then(([sum, shapData]) => {
        if (cancelled) return
        setSummary(sum)
        setShap(shapData)
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
  }, [casNumber, regulationId])

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md border-l bg-card shadow-xl flex flex-col animate-in slide-in-from-right">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h2 className="font-semibold text-sm">Substance Details</h2>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Close
        </Button>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-4">
        {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

        {error && <p className="text-sm text-destructive">{error}</p>}

        {!loading && summary && (
          <div className="rounded-lg border bg-muted/50 p-3 space-y-1">
            <p className="text-sm font-medium">{summary.name || 'Unknown substance'}</p>
            <p className="text-xs font-mono text-muted-foreground">{summary.casNumber || casNumber}</p>
          </div>
        )}

        {!loading && !summary && !error && (
          <p className="text-sm text-muted-foreground">No substance summary available.</p>
        )}

        {shap && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium">ML Risk Explanation</h3>
            <p className="text-xs text-muted-foreground">
              Predicted risk: <span className="font-medium">{(shap.predictedRisk * 100).toFixed(1)}%</span>
            </p>
            <div className="space-y-1">
              {shap.topFeatures.slice(0, 10).map((feature) => (
                <div
                  key={feature.feature}
                  className="flex items-center justify-between text-xs py-1 border-b last:border-b-0"
                >
                  <span className="text-muted-foreground truncate max-w-[60%]">{feature.feature}</span>
                  <span
                    className={[
                      'font-medium tabular-nums',
                      feature.contribution > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400',
                    ].join(' ')}
                  >
                    {feature.contribution > 0 ? '+' : ''}
                    {feature.contribution.toFixed(3)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {!shap && !loading && regulationId && (
          <p className="text-sm text-muted-foreground">No ML explanation available for this regulation.</p>
        )}
      </div>
    </div>
  )
}
