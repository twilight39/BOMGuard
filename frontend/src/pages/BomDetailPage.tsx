import { useEffect, useState } from 'react'
import { useParams, useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { fetchBom, deleteBom } from '@/services/api'
import type { BomDetail } from '@/types'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'

ModuleRegistry.registerModules([AllCommunityModule])

export function BomDetailPage() {
  const { bomId } = useParams({ from: '/boms/$bomId' })
  const navigate = useNavigate()
  const [bom, setBom] = useState<BomDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const id = Number(bomId)
  const isInvalidId = Number.isNaN(id)

  useEffect(() => {
    let cancelled = false
    fetchBom(id)
      .then((data) => {
        if (!cancelled) setBom(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load BOM')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id])

  const handleDelete = async () => {
    if (!bom) return
    if (!confirm('Delete this BOM?')) return
    await deleteBom(bom.id)
    navigate({ to: '/boms' })
  }

  if (isInvalidId) {
    return (
      <div className="p-6">
        <div className="rounded-md bg-destructive/10 text-destructive text-sm p-3">
          Invalid BOM ID
        </div>
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
        <div className="rounded-md bg-destructive/10 text-destructive text-sm p-3">
          {error || 'BOM not found'}
        </div>
      </div>
    )
  }

  const partColumns = [
    { headerName: 'Line', field: 'lineNumber' as const, width: 80 },
    { headerName: 'Part Number', field: 'partNumber' as const, flex: 2 },
    { headerName: 'Description', field: 'description' as const, flex: 2 },
    { headerName: 'Manufacturer', field: 'manufacturer' as const, flex: 1 },
    { headerName: 'Supplier', field: 'supplier' as const, flex: 1 },
    { headerName: 'CAS', field: 'casNumbers' as const, flex: 1 },
    { headerName: 'Qty', field: 'quantity' as const, width: 90 },
    { headerName: 'Unit', field: 'unit' as const, width: 90 },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold">{bom.name}</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {bom.fileFormat?.toUpperCase() ?? 'Unknown'} · {bom.totalParts} parts · Status:{' '}
            <span className="capitalize">{bom.complianceStatus}</span>
            {bom.createdAt && ` · ${new Date(bom.createdAt).toLocaleString()}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => navigate({ to: `/scan/${bom.id}` })}
          >
            Scan
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            Delete
          </Button>
        </div>
      </div>

      <div className="rounded-lg border bg-card">
        <div className="px-4 py-3 border-b font-medium text-sm">Parts</div>
        <div className="ag-theme-alpine">
          <AgGridReact
            rowData={bom.parts}
            columnDefs={partColumns}
            domLayout="autoHeight"
            pagination
            paginationPageSize={50}
          />
        </div>
      </div>
    </div>
  )
}
