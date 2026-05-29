import { useEffect, useState } from 'react'
import { fetchHealth } from '@/services/api'

function StatCard({ title, value, subtitle }: { title: string; value: string; subtitle?: string }) {
  return (
    <div className="rounded-lg border bg-card p-5">
      <p className="text-sm text-muted-foreground">{title}</p>
      <p className="text-2xl font-heading font-bold mt-1">{value}</p>
      {subtitle && <p className="text-xs text-muted-foreground mt-2">{subtitle}</p>}
    </div>
  )
}

export function DashboardPage() {
  const [health, setHealth] = useState<string>('checking…')

  useEffect(() => {
    fetchHealth()
      .then((r) => setHealth(r.status ?? 'unknown'))
      .catch(() => setHealth('offline'))
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-bold">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Overview of regulatory coverage, BOMs, and system health.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Substances" value="—" subtitle="from ECHA SVHC" />
        <StatCard title="Regulations" value="1" subtitle="EU REACH SVHC active" />
        <StatCard title="BOMs Uploaded" value="0" subtitle="pending scans" />
        <StatCard title="API Status" value={health} subtitle="backend health check" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-lg border bg-card p-5">
          <h3 className="font-medium text-sm">Recent Regulatory Changes</h3>
          <p className="text-sm text-muted-foreground mt-4">No changes detected yet.</p>
        </div>
        <div className="rounded-lg border bg-card p-5">
          <h3 className="font-medium text-sm">Recent Scans</h3>
          <p className="text-sm text-muted-foreground mt-4">No scans run yet.</p>
        </div>
      </div>
    </div>
  )
}
