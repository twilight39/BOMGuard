import { useCallback, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { uploadBom } from '@/services/api'

export function BomUpload() {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const handleFile = useCallback(
    async (file: File) => {
      setError(null)
      setIsUploading(true)
      try {
        const result = await uploadBom(file)
        navigate({ to: `/boms/${result.id}` })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed')
      } finally {
        setIsUploading(false)
      }
    },
    [navigate]
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

  return (
    <div className="space-y-4">
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
            {isUploading ? (
              <span className="inline-flex items-center gap-2">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                Uploading...
              </span>
            ) : (
              <>
                <p className="font-medium">Drop a BOM file here, or click to browse</p>
                <p className="text-xs mt-1">Supports CSV, XLSX, XLS</p>
              </>
            )}
          </div>
        </label>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 text-destructive text-sm p-3">
          {error}
        </div>
      )}
    </div>
  )
}
