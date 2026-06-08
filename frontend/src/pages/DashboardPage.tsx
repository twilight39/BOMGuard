import { useEffect, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { fetchHealth, fetchStats, fetchRecentScans, type RecentScan } from '@/services/api'
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

function StatusBadge({ status }: { status: string }) {
  const color =
    status === 'compliant'
      ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
      : status === 'non_compliant'
        ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
        : 'bg-muted text-muted-foreground'
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${color}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

export function DashboardPage() {
  const navigate = useNavigate()
  const [health, setHealth] = useState<string>('checking…')
  const [stats, setStats] = useState({ substances: 0, regulations: 0, boms: 0 })
  const [recentScans, setRecentScans] = useState<RecentScan[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetchHealth().then((r) => setHealth(r.status ?? 'unknown')).catch(() => setHealth('offline')),
      fetchStats().then(setStats).catch(() => setStats({ substances: 0, regulations: 0, boms: 0 })),
      fetchRecentScans(5)
        .then(setRecentScans)
        .catch(() => setRecentScans([])),
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
          {recentScans.length === 0 ? (
            <p className="text-sm text-muted-foreground mt-4">No scans run yet.</p>
          ) : (
            <div className="mt-3 space-y-2">
              {recentScans.map((scan) => (
                <button
                  key={scan.bomId}
                  onClick={() => navigate({ to: `/scan/${scan.bomId}` })}
                  className="w-full text-left flex items-center justify-between rounded-md px-3 py-2 hover:bg-muted transition-colors"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{scan.bomName}</p>
                    <p className="text-xs text-muted-foreground">
                      {scan.hitsFound} hit{scan.hitsFound === 1 ? '' : 's'}
                    </p>
                  </div>
                  <StatusBadge status={scan.complianceStatus} />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
