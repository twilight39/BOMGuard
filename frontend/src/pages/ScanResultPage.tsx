import { useEffect, useState } from 'react'
import { useParams, useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { fetchBom, triggerScan, fetchScanResults } from '@/services/api'
import type { BomDetail, ScanResult } from '@/types'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'

ModuleRegistry.registerModules([AllCommunityModule])

const severityBadge = (severity: string) => {
  const map: Record<string, string> = {
    critical: 'bg-destructive text-destructive-foreground',
    high: 'bg-orange-500 text-white',
    medium: 'bg-yellow-500 text-black',
    low: 'bg-blue-500 text-white',
    clean: 'bg-muted text-muted-foreground',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${map[severity] || map.low}`}>
      {severity}
    </span>
  )
}

export function ScanResultPage() {
  const { bomId } = useParams({ from: '/scan/$bomId' })
  const navigate = useNavigate()
  const [bom, setBom] = useState<BomDetail | null>(null)
  const [results, setResults] = useState<ScanResult[]>([])
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const id = Number(bomId)

  const loadAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const [bomData, resultData] = await Promise.all([
        fetchBom(id),
        fetchScanResults(id),
      ])
      setBom(bomData)
      setResults(resultData.results)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!Number.isNaN(id)) {
      loadAll()
    }
  }, [id])

  const handleScan = async () => {
    setScanning(true)
    setError(null)
    try {
      await triggerScan(id)
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed')
    } finally {
      setScanning(false)
    }
  }

  if (Number.isNaN(id)) {
    return (
      <div className="p-6">
        <div className="rounded-md bg-destructive/10 text-destructive text-sm p-3">Invalid BOM ID</div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-muted-foreground text-sm">Loading...</div>
      </div>
    )
  }

  if (error || !bom) {
    return (
      <div className="p-6">
        <div className="rounded-md bg-destructive/10 text-destructive text-sm p-3">{error || 'BOM not found'}</div>
      </div>
    )
  }

  const resultColumns = [
    { headerName: 'CAS Number', field: 'casNumber' as const, flex: 1 },
    { headerName: 'Regulation', field: 'regulationId' as const, flex: 2 },
    {
      headerName: 'Severity',
      field: 'severity' as const,
      width: 120,
      cellRenderer: (p: { value: string }) => severityBadge(p.value),
    },
    {
      headerName: 'Risk Score',
      field: 'riskScore' as const,
      width: 120,
      valueFormatter: (p: { value: number | null }) => (p.value != null ? p.value.toFixed(2) : '-'),
    },
    {
      headerName: 'Hit Type',
      field: 'hitType' as const,
      width: 140,
      cellRenderer: (p: { value: string }) => (
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize bg-muted">
          {p.value?.replace('_', ' ')}
        </span>
      ),
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold">Scan Results</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {bom.name} · {bom.totalParts} parts · Status:{' '}
            <span className="capitalize font-medium">{bom.complianceStatus}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => navigate({ to: `/boms/${bom.id}` })}>
            Back to BOM
          </Button>
          <Button onClick={handleScan} disabled={scanning}>
            {scanning ? (
              <span className="inline-flex items-center gap-2">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                Scanning...
              </span>
            ) : (
              'Re-scan'
            )}
          </Button>
        </div>
      </div>

      {bom.complianceStatus === 'pending' && results.length === 0 && (
        <div className="rounded-lg border bg-card p-8 text-center text-muted-foreground">
          <p>This BOM has not been scanned yet.</p>
          <Button className="mt-4" onClick={handleScan} disabled={scanning}>
            Run Scan
          </Button>
        </div>
      )}

      {bom.complianceStatus === 'clean' && results.length === 0 && (
        <div className="rounded-lg border bg-green-50 dark:bg-green-950/30 p-8 text-center">
          <p className="text-green-700 dark:text-green-400 font-medium">No compliance issues found</p>
          <p className="text-muted-foreground text-sm mt-1">All CAS numbers passed rule-based checks.</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="rounded-lg border bg-card">
          <div className="px-4 py-3 border-b font-medium text-sm">
            {results.length} hit{results.length !== 1 ? 's' : ''} found
          </div>
          <div className="ag-theme-alpine">
            <AgGridReact
              rowData={results}
              columnDefs={resultColumns}
              domLayout="autoHeight"
              pagination
              paginationPageSize={20}
            />
          </div>
        </div>
      )}
    </div>
  )
}
