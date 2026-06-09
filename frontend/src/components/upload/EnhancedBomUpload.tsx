import { useCallback, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { uploadBom } from '@/services/api'

interface PreviewData {
  headers: string[]
  rows: string[][]
  detectedHeaders: Record<string, string | null>
}

const EXPECTED_HEADERS = ['part_number', 'description', 'manufacturer', 'supplier', 'quantity', 'cas_numbers']

function detectMapping(headers: string[]): Record<string, string | null> {
  const mapping: Record<string, string | null> = {}
  const lowerHeaders = headers.map((h) => h.toLowerCase())

  for (const expected of EXPECTED_HEADERS) {
    const idx = lowerHeaders.findIndex((h) =>
      h.includes(expected.replace('_', '')) ||
      h.includes(expected) ||
      (expected === 'part_number' && (h.includes('part') || h.includes('mpn'))) ||
      (expected === 'cas_numbers' && (h.includes('cas') || h.includes('chemical')))
    )
    mapping[expected] = idx >= 0 ? headers[idx] : null
  }

  return mapping
}

async function parseCsvPreview(file: File, maxRows: number = 10): Promise<PreviewData | null> {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = () => {
      const text = String(reader.result || '')
      const lines = text.split(/\r?\n/).filter((l) => l.trim())
      if (lines.length === 0) return resolve(null)

      const headers = lines[0].split(',').map((h) => h.trim())
      const rows = lines
        .slice(1, maxRows + 1)
        .map((line) => line.split(',').map((cell) => cell.trim()))

      resolve({ headers, rows, detectedHeaders: detectMapping(headers) })
    }
    reader.onerror = () => resolve(null)
    reader.readAsText(file)
  })
}

export function EnhancedBomUpload() {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<PreviewData | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [progress, setProgress] = useState(0)
  const navigate = useNavigate()

  const handleFile = useCallback(
    async (file: File) => {
      setError(null)
      setSelectedFile(file)
      setProgress(0)

      if (file.name.endsWith('.csv')) {
        const data = await parseCsvPreview(file)
        setPreview(data)
      } else {
        setPreview(null)
      }
    },
    []
  )

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setIsDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile]
  )

  const onDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const onDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  const confirmUpload = async () => {
    if (!selectedFile) return
    setIsUploading(true)
    setProgress(20)
    try {
      const result = await uploadBom(selectedFile)
      setProgress(100)
      navigate({ to: `/boms/${result.id}` })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setProgress(0)
    } finally {
      setIsUploading(false)
    }
  }

  const clearSelection = () => {
    setSelectedFile(null)
    setPreview(null)
    setError(null)
    setProgress(0)
  }

  return (
    <div className="space-y-4">
      {!selectedFile ? (
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          className={[
            'border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer',
            isDragging
              ? 'border-primary bg-primary/5'
              : 'border-border bg-card hover:bg-muted/50',
          ].join(' ')}
        >
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={onInputChange}
            className="hidden"
            id="bom-upload-input"
          />
          <label htmlFor="bom-upload-input" className="cursor-pointer block">
            <div className="text-muted-foreground text-sm">
              <p className="font-medium">Drop a BOM file here, or click to browse</p>
              <p className="text-xs mt-1">Supports CSV, XLSX, XLS</p>
            </div>
          </label>
        </div>
      ) : (
        <div className="rounded-lg border bg-card p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{selectedFile.name}</p>
              <p className="text-xs text-muted-foreground">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={clearSelection} disabled={isUploading}>
              Change file
            </Button>
          </div>

          {preview && (
            <div className="space-y-3">
              <div className="rounded-md border overflow-auto max-h-48">
                <table className="w-full text-xs">
                  <thead className="bg-muted">
                    <tr>
                      {preview.headers.map((h) => (
                        <th key={h} className="px-2 py-1 text-left font-medium whitespace-nowrap">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row, i) => (
                      <tr key={i} className="border-b last:border-b-0">
                        {row.map((cell, j) => (
                          <td key={j} className="px-2 py-1 whitespace-nowrap">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="px-2 py-1 text-xs text-muted-foreground bg-muted/50">
                  Showing first {preview.rows.length} rows
                </p>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium">Detected column mapping</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(preview.detectedHeaders).map(([expected, detected]) => (
                    <div
                      key={expected}
                      className={[
                        'flex items-center justify-between rounded px-2 py-1',
                        detected ? 'bg-green-50 dark:bg-green-950/30' : 'bg-muted',
                      ].join(' ')}
                    >
                      <span className="text-muted-foreground capitalize">
                        {expected.replace('_', ' ')}
                      </span>
                      <span className={detected ? 'text-green-700 dark:text-green-400' : 'text-destructive'}>
                        {detected || 'Not found'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {isUploading && (
            <div className="space-y-1">
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full bg-primary transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground">Uploading… {progress}%</p>
            </div>
          )}

          <div className="flex items-center gap-2">
            <Button onClick={confirmUpload} disabled={isUploading} className="flex-1">
              {isUploading ? 'Uploading…' : 'Upload BOM'}
            </Button>
            <Button variant="outline" onClick={clearSelection} disabled={isUploading}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-md bg-destructive/10 text-destructive text-sm p-3">
          {error}
        </div>
      )}
    </div>
  )
}
