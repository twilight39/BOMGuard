import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { fetchBom, triggerScan, fetchScanResults } from '@/services/api'
import type { BomDetail, ScanResult } from '@/types'
import { useAgGridTheme } from '@/hooks/useAgGridTheme'
import { RiskBadge, RegulationBadge } from '@/components/scan-result/RiskBadge'
import { ScanResultDetail } from '@/components/scan-result/ScanResultDetail'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
import type { ColDef, GridApi } from 'ag-grid-community'

ModuleRegistry.registerModules([AllCommunityModule])

type ColumnKey = 'partNumber' | 'partDescription' | 'casNumber' | 'regulationId' | 'severity' | 'riskScore' | 'hitType'

const DEFAULT_VISIBLE: ColumnKey[] = [
  'partNumber',
  'partDescription',
  'casNumber',
  'regulationId',
  'severity',
  'riskScore',
  'hitType',
]

const COLUMN_LABELS: Record<ColumnKey, string> = {
  partNumber: 'Part Number',
  partDescription: 'Description',
  casNumber: 'CAS Number',
  regulationId: 'Regulation',
  severity: 'Severity',
  riskScore: 'Risk Score',
  hitType: 'Hit Type',
}

export function ScanResultPage() {
  const agGridTheme = useAgGridTheme()
  const { bomId } = useParams({ from: '/scan/$bomId' })
  const navigate = useNavigate()
  const [bom, setBom] = useState<BomDetail | null>(null)
  const [results, setResults] = useState<ScanResult[]>([])
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showColumnMenu, setShowColumnMenu] = useState(false)
  const [visibleCols, setVisibleCols] = useState<Set<ColumnKey>>(new Set(DEFAULT_VISIBLE))
  const [detailCas, setDetailCas] = useState<string | null>(null)
  const [detailReg, setDetailReg] = useState<string | null>(null)
  const gridApiRef = useRef<GridApi<ScanResult> | null>(null)

  const id = Number(bomId)

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [bomData, resultData] = await Promise.all([
        fetchBom(id),
        fetchScanResults(id),
      ])
      setBom(bomData)
      setResults(resultData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    if (Number.isNaN(id)) return
    const load = async () => {
      await loadAll()
    }
    load()
  }, [id, loadAll])

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

  const toggleColumn = (key: ColumnKey) => {
    const next = new Set(visibleCols)
    if (next.has(key)) {
      next.delete(key)
    } else {
      next.add(key)
    }
    setVisibleCols(next)
    gridApiRef.current?.setColumnsVisible([key], next.has(key))
  }

  const allColumns: ColDef<ScanResult>[] = useMemo(
    () => [
      { headerName: 'Part Number', field: 'partNumber', width: 140 },
      { headerName: 'Description', field: 'partDescription', flex: 2 },
      { headerName: 'CAS Number', field: 'casNumber', flex: 1 },
      {
        headerName: 'Regulation',
        field: 'regulationId',
        flex: 2,
        cellRenderer: (p: { value?: string | null }) => <RegulationBadge regulationId={p.value} />,
      },
      {
        headerName: 'Severity',
        field: 'severity',
        width: 120,
        cellRenderer: (p: { value?: string | null }) => <RiskBadge severity={p.value} />,
      },
      {
        headerName: 'Risk Score',
        field: 'riskScore',
        width: 120,
        valueFormatter: (p) => (p.value != null ? p.value.toFixed(2) : '-'),
      },
      {
        headerName: 'Hit Type',
        field: 'hitType',
        width: 160,
        valueFormatter: (p) => p.value?.replace(/_/g, ' ') || '—',
        cellClass: (p) =>
          p.value === 'unknown_cas' ? 'text-yellow-600 dark:text-yellow-400 italic' : '',
      },
    ],
    []
  )

  const columnDefs = useMemo(
    () => allColumns.filter((c) => visibleCols.has(c.field as ColumnKey)),
    [allColumns, visibleCols]
  )

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

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-heading font-bold">Scan Results</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {bom.name} · {bom.totalParts} parts · Status:{' '}
            <span className="capitalize font-medium">{bom.complianceStatus}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Button variant="ghost" size="sm" onClick={() => setShowColumnMenu((s) => !s)}>
              Columns
            </Button>
            {showColumnMenu && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setShowColumnMenu(false)}
                />
                <div className="absolute right-0 top-full mt-1 z-50 w-48 rounded-md border bg-popover shadow-md p-2 space-y-1">
                  {(Object.keys(COLUMN_LABELS) as ColumnKey[]).map((key) => (
                    <label
                      key={key}
                      className="flex items-center gap-2 px-2 py-1.5 rounded-sm hover:bg-accent cursor-pointer text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={visibleCols.has(key)}
                        onChange={() => toggleColumn(key)}
                        className="size-4 accent-primary"
                      />
                      {COLUMN_LABELS[key]}
                    </label>
                  ))}
                </div>
              </>
            )}
          </div>
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

      {error && (
        <div className="rounded-md bg-destructive/10 text-destructive text-sm p-3 shrink-0">
          {error}
        </div>
      )}

      {bom.complianceStatus === 'pending' && results.length === 0 && (
        <div className="rounded-lg border bg-card p-8 text-center text-muted-foreground shrink-0">
          <p>This BOM has not been scanned yet.</p>
          <Button className="mt-4" onClick={handleScan} disabled={scanning}>
            Run Scan
          </Button>
        </div>
      )}

      {bom.complianceStatus === 'clean' && results.length === 0 && (
        <div className="rounded-lg border bg-green-50 dark:bg-green-950/30 p-8 text-center shrink-0">
          <p className="text-green-700 dark:text-green-400 font-medium">No compliance issues found</p>
          <p className="text-muted-foreground text-sm mt-1">All CAS numbers passed rule-based checks.</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="flex-1 min-h-0 rounded-lg border bg-card overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b font-medium text-sm shrink-0">
            {results.length} hit{results.length !== 1 ? 's' : ''} found
          </div>
          <div className="flex-1 min-h-0">
            <AgGridReact
              theme={agGridTheme}
              rowData={results}
              columnDefs={columnDefs}
              getRowId={(params) => String(params.data.id)}
              onGridReady={(params) => {
                gridApiRef.current = params.api
              }}
              onRowClicked={(params) => {
                if (params.data?.casNumber) {
                  setDetailCas(params.data.casNumber)
                  setDetailReg(params.data.regulationId || null)
                }
              }}
            />
          </div>
        </div>
      )}

      {detailCas && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/20"
            onClick={() => setDetailCas(null)}
          />
          <ScanResultDetail
            casNumber={detailCas}
            regulationId={detailReg || undefined}
            onClose={() => setDetailCas(null)}
          />
        </>
      )}
    </div>
  )
}
