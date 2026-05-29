import { useParams } from '@tanstack/react-router'

export function ScanResultPage() {
  const { bomId } = useParams({ from: '/scan/$bomId' })

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-bold">Scan Result</h1>
        <p className="text-muted-foreground text-sm mt-1">BOM ID: {bomId}</p>
      </div>
      <div className="rounded-lg border bg-card p-8 text-center text-muted-foreground">
        Scan result placeholder
      </div>
    </div>
  )
}
