import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { fetchBoms, triggerScan } from '@/services/api'
import type { Bom } from '@/types'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
import type { CellClickedEvent } from 'ag-grid-community'

ModuleRegistry.registerModules([AllCommunityModule])

function ScanNewPage() {
  const navigate = useNavigate()
  const [boms, setBoms] = useState<Bom[]>([])
  const [loading, setLoading] = useState(true)
  const [scanningId, setScanningId] = useState<number | null>(null)

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

  const onRowClicked = (event: CellClickedEvent<Bom>) => {
    if (event.data) {
      navigate({ to: `/boms/${event.data.id}` })
    }
  }

  const columnDefs = [
    {
      headerName: 'Name',
      field: 'name' as const,
      flex: 2,
      cellClass: 'cursor-pointer',
    },
    { headerName: 'Format', field: 'fileFormat' as const, width: 100 },
    { headerName: 'Parts', field: 'totalParts' as const, width: 100 },
    {
      headerName: 'Status',
      field: 'complianceStatus' as const,
      width: 120,
      cellRenderer: (p: { value: string }) => (
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize bg-muted">
          {p.value}
        </span>
      ),
    },
    {
      headerName: '',
      width: 120,
      sortable: false,
      filter: false,
      cellRenderer: (p: { data: Bom }) => (
        <Button
          size="sm"
          disabled={scanningId === p.data.id}
          onClick={(e) => {
            e.stopPropagation()
            handleScan(p.data.id)
          }}
        >
          {scanningId === p.data.id ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
              Scanning
            </span>
          ) : (
            'Scan'
          )}
        </Button>
      ),
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-bold">Scan</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Select a BOM to run a compliance scan.
        </p>
      </div>

      <div className="rounded-lg border bg-card">
        {loading ? (
          <div className="p-8 text-center text-muted-foreground text-sm">Loading...</div>
        ) : boms.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-muted-foreground text-sm">No BOMs available.</p>
            <p className="text-muted-foreground text-xs mt-1">
              Upload a BOM first, or load a sample from the BOMs page.
            </p>
          </div>
        ) : (
          <div className="ag-theme-alpine">
            <AgGridReact
              rowData={boms}
              columnDefs={columnDefs}
              domLayout="autoHeight"
              pagination
              paginationPageSize={20}
              onRowClicked={onRowClicked}
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
