import { useEffect, useRef, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { fetchBoms, loadSample, fetchSampleList, uploadBom } from '@/services/api'
import type { Bom } from '@/types'
import { useAgGridTheme } from '@/hooks/useAgGridTheme'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
import type { ColDef } from 'ag-grid-community'

ModuleRegistry.registerModules([AllCommunityModule])

const SAMPLES_DISMISSED_KEY = 'bomguard_samples_dismissed'

interface SampleMeta {
  id: string
  name: string
  filename: string
}

export function BomsPage() {
  const agGridTheme = useAgGridTheme()
  const [boms, setBoms] = useState<Bom[]>([])
  const [loading, setLoading] = useState(true)
  const [samples, setSamples] = useState<SampleMeta[]>([])
  const [showSamples, setShowSamples] = useState(() => {
    try {
      return localStorage.getItem(SAMPLES_DISMISSED_KEY) !== 'true'
    } catch {
      return true
    }
  })
  const [loadingSample, setLoadingSample] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
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

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const result = await uploadBom(file)
      navigate({ to: `/boms/${result.id}` })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const columnDefs: ColDef<Bom>[] = [
    { headerName: 'Name', field: 'name', flex: 2, cellClass: 'cursor-pointer' },
    { headerName: 'Format', field: 'fileFormat', width: 100 },
    { headerName: 'Parts', field: 'totalParts', width: 100 },
    {
      headerName: 'Status',
      field: 'complianceStatus',
      width: 140,
      valueFormatter: (p) => {
        const status = p.value as string
        const hits = p.data?.hitCount ?? 0
        if (status === 'flagged' || status === 'review') {
          return `${status} (${hits})`
        }
        return status
      },
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
  ]

  const showSampleSection = boms.length === 0 && !loading && showSamples

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex items-center justify-between shrink-0">
        <h1 className="text-2xl font-heading font-bold">BOMs</h1>
        <Button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? (
            <span className="inline-flex items-center gap-2">
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
              Uploading…
            </span>
          ) : (
            'Upload BOM'
          )}
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {showSampleSection && (
        <div className="rounded-xl border bg-card p-6 space-y-4 relative shrink-0">
          <button
            onClick={dismissSamples}
            className="absolute top-3 right-3 text-muted-foreground hover:text-foreground text-lg leading-none px-2 py-1 rounded-md hover:bg-muted transition-colors cursor-pointer"
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
                className="text-left rounded-lg border bg-background p-4 space-y-2 hover:border-primary/50 hover:shadow-sm transition-all disabled:opacity-60 cursor-pointer"
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

      <div className="flex-1 min-h-0 rounded-lg border bg-card overflow-hidden">
        {loading ? (
          <div className="h-full flex items-center justify-center text-muted-foreground text-sm">Loading...</div>
        ) : boms.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center">
            <p className="text-muted-foreground text-sm">No BOMs uploaded yet.</p>
            <p className="text-muted-foreground text-xs mt-1">Upload a CSV or XLSX to get started.</p>
          </div>
        ) : (
          <div className="h-full">
            <AgGridReact
              theme={agGridTheme}
              rowData={boms}
              columnDefs={columnDefs}
              getRowId={(params) => String(params.data.id)}
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
