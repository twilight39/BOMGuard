import { useParams } from '@tanstack/react-router'

export function ScanResultPage() {
  const { bomId } = useParams({ from: '/scan/$bomId' })

  return (
    <div className="p-8">
      <h1 className="text-2xl font-heading font-bold">Scan Result</h1>
      <p className="text-muted-foreground">BOM ID: {bomId}</p>
    </div>
  )
}
