interface RiskBadgeProps {
  severity?: string | null
}

export function RiskBadge({ severity }: RiskBadgeProps) {
  const colorClasses =
    severity === 'critical'
      ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
      : severity === 'high'
        ? 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300'
        : severity === 'medium'
          ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
          : severity === 'unknown'
            ? 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 italic'
            : 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'

  const label = severity?.replace(/_/g, ' ') || 'clean'

  return (
    <span className={['inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', colorClasses].join(' ')}>
      {label}
    </span>
  )
}

export function RegulationBadge({ regulationId }: { regulationId?: string | null }) {
  if (!regulationId) return <span className="text-xs text-muted-foreground">—</span>
  const label = regulationId
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
  return (
    <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs bg-muted text-muted-foreground">
      {label}
    </span>
  )
}
