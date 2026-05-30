import { useEffect, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { BomUpload } from '@/components/bom/BomUpload'
import { fetchBoms, deleteBom, loadSample, fetchSampleList } from '@/services/api'
import type { Bom } from '@/types'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'

ModuleRegistry.registerModules([AllCommunityModule])

const SAMPLES_DISMISSED_KEY = 'bomguard_samples_dismissed'

interface SampleMeta {
  id: string
  name: string
  filename: string
}

export function BomsPage() {
  const [boms, setBoms] = useState<Bom[]>([])
  const [loading, setLoading] = useState(true)
  const [showUpload, setShowUpload] = useState(false)
  const [samples, setSamples] = useState<SampleMeta[]>([])
  const [showSamples, setShowSamples] = useState(() => {
    try {
      return localStorage.getItem(SAMPLES_DISMISSED_KEY) !== 'true'
    } catch {
      return true
    }
  })
  const [loadingSample, setLoadingSample] = useState<string | null>(null)
  const navigate = useNavigate()

  const loadBoms = async () => {
    setLoading(true)
    try {
      const data = await fetchBoms()
      setBoms(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadBoms()
    fetchSampleList().then(setSamples).catch(() => setSamples([]))
  }, [])

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this BOM?')) return
    await deleteBom(id)
    setBoms((prev) => prev.filter((b) => b.id !== id))
  }

  const handleLoadSample = async (sampleId: string) => {
    setLoadingSample(sampleId)
    try {
      await loadSample(sampleId)
      await loadBoms()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to load sample')
    } finally {
      setLoadingSample(null)
    }
  }

  const dismissSamples = () => {
    setShowSamples(false)
    try {
      localStorage.setItem(SAMPLES_DISMISSED_KEY, 'true')
    } catch {
      // ignore
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
    {
      headerName: 'Created',
      field: 'createdAt',
      width: 160,
      valueFormatter: (p: { value: string | null }) =>
        p.value ? new Date(p.value).toLocaleString() : '-',
    },
  ]

  const showSampleSection = boms.length === 0 && !loading && showSamples

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-bold">BOMs</h1>
        <Button onClick={() => setShowUpload((s) => !s)}>
          {showUpload ? 'Close Upload' : 'Upload BOM'}
        </Button>
      </div>

      {showUpload && <BomUpload />}

      {showSampleSection && (
        <div className="rounded-xl border bg-card p-6 space-y-4 relative">
          <button
            onClick={dismissSamples}
            className="absolute top-3 right-3 text-muted-foreground hover:text-foreground text-lg leading-none px-2 py-1 rounded-md hover:bg-muted transition-colors"
            aria-label="Dismiss"
            title="Dismiss"
          >
            ×
          </button>
          <div>
            <h2 className="text-lg font-semibold">No BOMs on hand?</h2>
            <p className="text-muted-foreground text-sm mt-1">
              Try scanning one of these pre-built sample BOMs to see how compliance checking works.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {samples.map((sample) => (
              <button
                key={sample.id}
                onClick={() => handleLoadSample(sample.id)}
                disabled={loadingSample === sample.id}
                className="text-left rounded-lg border bg-background p-4 space-y-2 hover:border-primary/50 hover:shadow-sm transition-all disabled:opacity-60"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{sample.name}</span>
                  {loadingSample === sample.id && (
                    <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                  )}
                </div>
                <p className="text-xs text-muted-foreground">{sample.filename}</p>
                <span className="inline-flex items-center text-xs text-primary font-medium">Load sample →</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-lg border bg-card">
        {loading ? (
          <div className="p-8 text-center text-muted-foreground text-sm">Loading...</div>
        ) : boms.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-muted-foreground text-sm">No BOMs uploaded yet.</p>
            <p className="text-muted-foreground text-xs mt-1">Upload a CSV or XLSX to get started.</p>
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
    </div>
  )
}
