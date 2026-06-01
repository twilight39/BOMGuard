import { useEffect, useState } from 'react'
import { useParams, useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { fetchBom, deleteBom, triggerScan, fetchScanResults } from '@/services/api'
import type { BomDetail, BomPart, ScanResult } from '@/types'
import { useAgGridTheme } from '@/hooks/useAgGridTheme'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
import type { ColDef } from 'ag-grid-community'

ModuleRegistry.registerModules([AllCommunityModule])

const statusBadge = (status: string) => {
  const map: Record<string, string> = {
    clean: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-400',
    flagged: 'bg-destructive/10 text-destructive',
    review: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-400',
    pending: 'bg-muted text-muted-foreground',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${map[status] || map.pending}`}>
      {status}
    </span>
  )
}

export function BomDetailPage() {
  const agGridTheme = useAgGridTheme()
  const { bomId } = useParams({ from: '/boms/$bomId' })
  const navigate = useNavigate()
  const [bom, setBom] = useState<BomDetail | null>(null)
  const [scanResults, setScanResults] = useState<ScanResult[]>([])
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const id = Number(bomId)
  const isInvalidId = Number.isNaN(id)

  const loadAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const [bomData, resultData] = await Promise.all([
        fetchBom(id),
        fetchScanResults(id).catch(() => ({ bomId: id, status: 'pending', results: [] as ScanResult[] })),
      ])
      setBom(bomData)
      setScanResults(resultData.results)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load BOM')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isInvalidId) {
      loadAll()
    }
  }, [id])

  const handleDelete = async () => {
    if (!bom) return
    if (!confirm('Delete this BOM?')) return
    await deleteBom(bom.id)
    navigate({ to: '/boms' })
  }

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

  if (isInvalidId) {
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

  const partColumns: ColDef<BomPart>[] = [
    { headerName: 'Line', field: 'lineNumber', width: 80 },
    { headerName: 'Part Number', field: 'partNumber', flex: 2 },
    { headerName: 'Description', field: 'description', flex: 2 },
    { headerName: 'Manufacturer', field: 'manufacturer', flex: 1 },
    { headerName: 'Supplier', field: 'supplier', flex: 1 },
    { headerName: 'CAS', field: 'casNumbers', flex: 1 },
    { headerName: 'Qty', field: 'quantity', width: 90 },
    { headerName: 'Unit', field: 'unit', width: 90 },
  ]

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-heading font-bold">{bom.name}</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {bom.fileFormat?.toUpperCase() ?? 'Unknown'} · {bom.totalParts} parts ·{' '}
            {statusBadge(bom.complianceStatus)}
            {bom.createdAt && ` · ${new Date(bom.createdAt).toLocaleString()}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleScan}
            disabled={scanning}
          >
            {scanning ? (
              <span className="inline-flex items-center gap-2">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                Scanning...
              </span>
            ) : (
              'Scan'
            )}
          </Button>
          {scanResults.length > 0 && (
            <Button
              variant="outline"
              onClick={() => navigate({ to: `/scan/${bom.id}` })}
            >
              View Results ({scanResults.length})
            </Button>
          )}
          <Button variant="destructive" onClick={handleDelete}>
            Delete
          </Button>
        </div>
      </div>

      {scanResults.length > 0 && (
        <div className="rounded-lg border bg-card p-4 space-y-3 shrink-0">
          <div className="flex items-center justify-between">
            <h2 className="font-medium text-sm">Latest Scan Summary</h2>
            <Button variant="ghost" size="sm" onClick={() => navigate({ to: `/scan/${bom.id}` })}>
              View full results →
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {Array.from(new Set(scanResults.map((r) => r.severity))).sort().map((sev) => (
              <span key={sev} className={[
                'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium capitalize',
                sev === 'unknown'
                  ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-400'
                  : 'bg-muted',
              ].join(' ')}>
                {sev}: {scanResults.filter((r) => r.severity === sev).length}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 min-h-0 rounded-lg border bg-card overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b font-medium text-sm shrink-0">Parts</div>
        <div className="flex-1 min-h-0">
          <AgGridReact
            theme={agGridTheme}
            rowData={bom.parts ?? []}
            columnDefs={partColumns}
            getRowId={(params) => String(params.data.id)}
          />
        </div>
      </div>
    </div>
  )
}
