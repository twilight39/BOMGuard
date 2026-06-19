import * as React from 'react'
import { Link } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import type { RegulatoryAlert } from '@/hooks/useRegulatoryAlerts'

interface RegulatoryAlertToastProps {
  alert: RegulatoryAlert
  onDismiss: () => void
}

function regulationLabel(id: string): string {
  const labels: Record<string, string> = {
    eu_reach_svhc: 'EU REACH SVHC',
    us_state_pfas: 'US State PFAS',
    eu_rohs: 'EU RoHS',
    us_tsca_6h: 'US TSCA 6(h)',
    cn_rohs: 'China RoHS 2',
  }
  return labels[id] || id
}

export function RegulatoryAlertToast({ alert, onDismiss }: RegulatoryAlertToastProps) {
  React.useEffect(() => {
    const timer = setTimeout(onDismiss, 8000)
    return () => clearTimeout(timer)
  }, [onDismiss])

  const totalChanges = alert.changesDetected

  return (
    <div className="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-lg border bg-card p-4 shadow-lg animate-in slide-in-from-right fade-in">
      <div className="flex-1">
        <p className="text-sm font-semibold text-foreground">
          {regulationLabel(alert.regulationId)} updated
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          {totalChanges} change{totalChanges !== 1 ? 's' : ''} detected
          {alert.substancesCreated > 0 && ` · ${alert.substancesCreated} new substance${alert.substancesCreated !== 1 ? 's' : ''}`}
        </p>
        <div className="mt-2 flex items-center gap-2">
          <Link
            to="/regulations"
            className="text-xs font-medium text-primary hover:underline"
            onClick={onDismiss}
          >
            View feed →
          </Link>
        </div>
      </div>
      <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={onDismiss}>
        ×
      </Button>
    </div>
  )
}
