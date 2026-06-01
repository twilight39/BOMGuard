import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState, useCallback, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { fetchBoms, triggerScan } from '@/services/api'
import type { Bom } from '@/types'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
import type { ColDef, ICellRendererParams } from 'ag-grid-community'

ModuleRegistry.registerModules([AllCommunityModule])

interface ScanActionCellProps extends ICellRendererParams<Bom> {
  scanningId: number | null
  scanningAll: boolean
  onScan: (bomId: number) => void
}

function ScanActionCell(props: ScanActionCellProps) {
  const bom = props.data
  if (!bom) return null
  const isScanning = props.scanningId === bom.id
  return (
    <div className="flex items-center justify-center h-full">
      <Button
        variant="outline"
        size="sm"
        disabled={isScanning || props.scanningAll}
        onClick={(e) => {
          e.stopPropagation()
          props.onScan(bom.id)
        }}
      >
        {isScanning ? (
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        ) : (
          'Scan'
        )}
      </Button>
    </div>
  )
}

function ScanNewPage() {
  const navigate = useNavigate()
  const [boms, setBoms] = useState<Bom[]>([])
  const [loading, setLoading] = useState(true)
  const [scanningId, setScanningId] = useState<number | null>(null)
  const [scanningAll, setScanningAll] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  useEffect(() => {
    fetchBoms()
      .then(setBoms)
      .finally(() => setLoading(false))
  }, [])

  const handleScan = async (bomId: number) => {
    setScanningId(bomId)
    try {
      await triggerScan(bomId)
      navigate({ to: `/scan/${bomId}` })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Scan failed')
      setScanningId(null)
    }
  }

  const handleScanAll = async () => {
    const ids = selectedIds.size > 0 ? Array.from(selectedIds) : boms.map((b) => b.id)
    if (ids.length === 0) return
    setScanningAll(true)
    try {
      await Promise.all(ids.map((id) => triggerScan(id)))
      navigate({ to: `/scan/${ids[0]}` })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Batch scan failed')
    } finally {
      setScanningAll(false)
    }
  }

  const onSelectionChanged = useCallback((event: { api: { getSelectedRows: () => Bom[] } }) => {
    const selected = event.api.getSelectedRows()
    setSelectedIds(new Set(selected.map((r) => r.id)))
  }, [])

  const scanCellRenderer = useCallback(
    (props: ICellRendererParams<Bom>) => (
      <ScanActionCell {...props} scanningId={scanningId} scanningAll={scanningAll} onScan={handleScan} />
    ),
    [scanningId, scanningAll]
  )

  const columnDefs: ColDef<Bom>[] = useMemo(
    () => [
      {
        headerName: '',
        width: 40,
        pinned: 'left',
        sortable: false,
        filter: false,
        suppressMovable: true,
        resizable: false,
      },
      { headerName: 'Name', field: 'name', flex: 2 },
      { headerName: 'Format', field: 'fileFormat', width: 100 },
      { headerName: 'Parts', field: 'totalParts', width: 100 },
      {
        headerName: 'Status',
        field: 'complianceStatus',
        width: 120,
        valueFormatter: (p) => p.value,
        cellClass: (p) =>
          p.value === 'flagged'
            ? 'text-destructive font-medium'
            : p.value === 'clean'
              ? 'text-green-600 dark:text-green-400 font-medium'
              : p.value === 'review'
                ? 'text-yellow-600 dark:text-yellow-400 font-medium'
                : '',
      },
      {
        headerName: 'Created',
        field: 'createdAt',
        width: 180,
        valueFormatter: (p) =>
          p.value ? new Date(p.value).toLocaleString() : '-',
      },
      {
        headerName: 'Action',
        width: 100,
        sortable: false,
        filter: false,
        suppressMovable: true,
        resizable: false,
        cellRenderer: scanCellRenderer,
      },
    ],
    [scanCellRenderer]
  )

  const scanLabel = selectedIds.size > 0
    ? `Scan Selected (${selectedIds.size})`
    : 'Scan All'

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-heading font-bold">Scan</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Select BOMs to run a compliance scan, or click Scan on a specific row.
          </p>
        </div>
        <Button
          onClick={handleScanAll}
          disabled={scanningAll || boms.length === 0}
        >
          {scanningAll ? (
            <span className="inline-flex items-center gap-2">
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
              Scanning…
            </span>
          ) : (
            scanLabel
          )}
        </Button>
      </div>

      <div className="flex-1 min-h-0 rounded-lg border bg-card overflow-hidden">
        {loading ? (
          <div className="h-full flex items-center justify-center text-muted-foreground text-sm">Loading...</div>
        ) : boms.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center">
            <p className="text-muted-foreground text-sm">No BOMs available.</p>
            <p className="text-muted-foreground text-xs mt-1">
              Upload a BOM first, or load a sample from the BOMs page.
            </p>
          </div>
        ) : (
          <div className="ag-theme-balham h-full">
            <AgGridReact
              rowData={boms}
              columnDefs={columnDefs}
              getRowId={(params) => String(params.data.id)}
              theme="legacy"
              rowSelection={{ mode: 'multiRow', checkboxes: true, headerCheckbox: true }}
              onSelectionChanged={onSelectionChanged}
              onRowClicked={(event) => {
                if (event.node) {
                  event.node.setSelected(!event.node.isSelected())
                }
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export const Route = createFileRoute('/scan/new')({
  component: ScanNewPage,
})
