import * as React from 'react'
import { Button } from '@/components/ui/button'
import { getEnrichmentStatus, triggerEnrichment } from '@/services/api'
import { MlDashboardCards } from '@/components/ml-dashboard/MlDashboardCards'

export function AdminPage() {
  const [status, setStatus] = React.useState<{
    substanceCount: number
    summaryCount: number
    missing: number
    complete: boolean
  } | null>(null)
  const [loading, setLoading] = React.useState(false)
  const [triggering, setTriggering] = React.useState(false)
  const [taskId, setTaskId] = React.useState<string | null>(null)

  const fetchStatus = React.useCallback(async () => {
    setLoading(true)
    try {
      const data = await getEnrichmentStatus()
      setStatus(data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    const run = async () => {
      await fetchStatus()
    }
    run()
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  const handleTrigger = async () => {
    setTriggering(true)
    try {
      const result = await triggerEnrichment()
      setTaskId(result.taskId)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to trigger enrichment')
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div className="p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-heading font-bold">ML Operations Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">Model metrics and enrichment status.</p>
      </div>

      <MlDashboardCards />

      <div className="rounded-xl border bg-card p-6 space-y-4">
        <h2 className="text-lg font-semibold">Regulatory Summary Enrichment</h2>
        <p className="text-sm text-muted-foreground">
          Generate AI summaries and embeddings for all substances. This powers the RAG chat assistant.
        </p>

        {status && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="rounded-lg bg-muted p-4 text-center">
              <div className="text-2xl font-bold">{status.substanceCount}</div>
              <div className="text-xs text-muted-foreground">Substances</div>
            </div>
            <div className="rounded-lg bg-muted p-4 text-center">
              <div className="text-2xl font-bold">{status.summaryCount}</div>
              <div className="text-xs text-muted-foreground">Summaries</div>
            </div>
            <div className="rounded-lg bg-muted p-4 text-center">
              <div className="text-2xl font-bold">{status.missing}</div>
              <div className="text-xs text-muted-foreground">Missing</div>
            </div>
            <div className="rounded-lg bg-muted p-4 text-center">
              <div className="text-2xl font-bold">
                {status.substanceCount > 0
                  ? Math.round((status.summaryCount / status.substanceCount) * 100)
                  : 0}
                %
              </div>
              <div className="text-xs text-muted-foreground">Coverage</div>
            </div>
          </div>
        )}

        <div className="flex items-center gap-3">
          <Button
            onClick={handleTrigger}
            disabled={triggering || loading || status?.complete}
          >
            {triggering ? 'Queueing…' : 'Generate All Summaries'}
          </Button>
          <Button variant="outline" onClick={fetchStatus} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh Status'}
          </Button>
        </div>

        {taskId && (
          <p className="text-xs text-muted-foreground">
            Task queued: <code className="bg-muted px-1 rounded">{taskId}</code>
          </p>
        )}
      </div>
    </div>
  )
}
