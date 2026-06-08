import * as React from 'react'
import { fetchRegulations, type Regulation } from '@/services/api'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

export function RegulationsPage() {
  const [regulations, setRegulations] = React.useState<Regulation[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    fetchRegulations()
      .then((data) => {
        setRegulations(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load regulations')
        setLoading(false)
      })
  }, [])

  return (
    <TooltipProvider>
      <div className="p-6 space-y-6">
        <h1 className="text-2xl font-heading font-bold">Regulations</h1>

        {loading && (
          <div className="text-muted-foreground text-sm animate-pulse">Loading…</div>
        )}

        {error && (
          <div className="text-destructive text-sm">{error}</div>
        )}

        {!loading && !error && (
          <div className="rounded-lg border bg-card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted">
                <tr>
                  <th className="text-left px-4 py-3 font-medium">ID</th>
                  <th className="text-left px-4 py-3 font-medium">Name</th>
                  <th className="text-left px-4 py-3 font-medium">Authority</th>
                  <th className="text-left px-4 py-3 font-medium">ML</th>
                </tr>
              </thead>
              <tbody>
                {regulations.length === 0 && (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-4 py-8 text-center text-muted-foreground"
                    >
                      No regulations found.
                    </td>
                  </tr>
                )}
                {regulations.map((reg) => (
                  <tr key={reg.id} className="border-b last:border-b-0">
                    <td className="px-4 py-3 font-mono text-xs">{reg.id}</td>
                    <td className="px-4 py-3">{reg.name}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {reg.authority ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      {reg.mlEnabled ? (
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
                          enabled
                        </span>
                      ) : (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs bg-muted text-muted-foreground cursor-help">
                              disabled
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Insufficient training data</p>
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </TooltipProvider>
  )
}
