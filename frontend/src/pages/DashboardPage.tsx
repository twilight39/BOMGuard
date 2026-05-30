import { useEffect, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { fetchHealth, fetchStats } from '@/services/api'
import { Button } from '@/components/ui/button'

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
  const navigate = useNavigate()
  const [health, setHealth] = useState<string>('checking…')
  const [stats, setStats] = useState({ substances: 0, regulations: 0, boms: 0 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetchHealth().then((r) => setHealth(r.status ?? 'unknown')).catch(() => setHealth('offline')),
      fetchStats().then(setStats).catch(() => setStats({ substances: 0, regulations: 0, boms: 0 })),
    ]).finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-bold">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Overview of regulatory coverage, BOMs, and system health.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Substances"
          value={loading ? '—' : String(stats.substances)}
          subtitle="from ECHA SVHC + EPA"
        />
        <StatCard
          title="Regulations"
          value={loading ? '—' : String(stats.regulations)}
          subtitle="active regulations tracked"
        />
        <StatCard
          title="BOMs Uploaded"
          value={loading ? '—' : String(stats.boms)}
          subtitle="pending scans"
        />
        <StatCard
          title="API Status"
          value={health}
          subtitle="backend health check"
        />
      </div>

      {stats.boms === 0 && !loading && (
        <div className="rounded-xl border bg-card p-6 space-y-3">
          <h2 className="text-lg font-semibold">Get started</h2>
          <p className="text-muted-foreground text-sm">
            Upload a BOM to start checking compliance against live regulatory data.
          </p>
          <div className="flex gap-3">
            <Button onClick={() => navigate({ to: '/boms' })}>Go to BOMs</Button>
            <Button variant="outline" onClick={() => navigate({ to: '/scan/new' })}>
              Start a Scan
            </Button>
          </div>
        </div>
      )}

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
