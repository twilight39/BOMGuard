import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { fetchBoms, triggerScan } from '@/services/api'
import type { Bom } from '@/types'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'

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

  const columnDefs = [
    { headerName: 'Name', field: 'name', flex: 2, cellClass: 'cursor-pointer' },
    { headerName: 'Format', field: 'fileFormat', width: 100 },
    { headerName: 'Parts', field: 'totalParts', width: 100 },
    {
      headerName: 'Status',
      field: 'complianceStatus',
      width: 120,
      valueFormatter: (p: { value: string }) => p.value,
      cellClass: (p: { value: string }) =>
        p.value === 'flagged'
          ? 'text-destructive font-medium'
          : p.value === 'clean'
            ? 'text-green-600 dark:text-green-400 font-medium'
            : p.value === 'review'
              ? 'text-yellow-600 dark:text-yellow-400 font-medium'
              : '',
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-bold">Scan</h1>
        <p className="text-muted-foreground text-sm mt-1">Select a BOM to run a compliance scan.</p>
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
          <div className="ag-theme-balham">
            <AgGridReact
              rowData={boms}
              columnDefs={columnDefs}
              domLayout="autoHeight"
              pagination
              paginationPageSize={20}
              onRowClicked={(event) => {
                if (event.data) {
                  navigate({ to: `/boms/${event.data.id}` })
                }
              }}
            />
          </div>
        )}
      </div>

      {boms.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {boms.map((bom) => (
            <Button
              key={bom.id}
              variant="outline"
              size="sm"
              disabled={scanningId === bom.id}
              onClick={() => handleScan(bom.id)}
            >
              {scanningId === bom.id ? (
                <span className="inline-flex items-center gap-1.5">
                  <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                  Scanning {bom.name}...
                </span>
              ) : (
                <>Scan {bom.name}</>
              )}
            </Button>
          ))}
        </div>
      )}
    </div>
  )
}

export const Route = createFileRoute('/scan/new')({
  component: ScanNewPage,
})
