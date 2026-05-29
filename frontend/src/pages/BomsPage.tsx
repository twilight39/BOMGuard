import { useEffect, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { BomUpload } from '@/components/bom/BomUpload'
import { fetchBoms, deleteBom } from '@/services/api'
import type { Bom } from '@/types'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'

ModuleRegistry.registerModules([AllCommunityModule])

export function BomsPage() {
  const [boms, setBoms] = useState<Bom[]>([])
  const [loading, setLoading] = useState(true)
  const [showUpload, setShowUpload] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false
    fetchBoms()
      .then((data) => {
        if (!cancelled) setBoms(data)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this BOM?')) return
    await deleteBom(id)
    setBoms((prev) => prev.filter((b) => b.id !== id))
  }

  const columnDefs = [
    {
      headerName: 'Name',
      field: 'name' as const,
      flex: 2,
      cellRenderer: (p: { value: string; data: Bom }) => (
        <button
          className="text-left text-primary hover:underline font-medium"
          onClick={() => navigate({ to: `/boms/${p.data.id}` })}
        >
          {p.value}
        </button>
      ),
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
      headerName: 'Created',
      field: 'createdAt' as const,
      width: 160,
      valueFormatter: (p: { value: string | null }) =>
        p.value ? new Date(p.value).toLocaleString() : '-',
    },
    {
      headerName: 'Actions',
      width: 120,
      cellRenderer: (p: { data: Bom }) => (
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate({ to: `/boms/${p.data.id}` })}
          >
            View
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive"
            onClick={() => handleDelete(p.data.id)}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-bold">BOMs</h1>
        <Button onClick={() => setShowUpload((s) => !s)}>
          {showUpload ? 'Close Upload' : 'Upload BOM'}
        </Button>
      </div>

      {showUpload && <BomUpload />}

      <div className="rounded-lg border bg-card">
        {loading ? (
          <div className="p-8 text-center text-muted-foreground text-sm">Loading...</div>
        ) : boms.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-muted-foreground text-sm">No BOMs uploaded yet.</p>
            <p className="text-muted-foreground text-xs mt-1">
              Upload a CSV or XLSX to get started.
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
            />
          </div>
        )}
      </div>
    </div>
  )
}
