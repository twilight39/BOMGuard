interface MlRiskBadgeProps {
  tier?: string | null
  score?: number | null
}

export function MlRiskBadge({ tier }: MlRiskBadgeProps) {
  if (!tier) {
    return <span className="text-xs text-muted-foreground">—</span>
  }

  const colorClasses =
    tier === 'high'
      ? 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300'
      : tier === 'medium'
        ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
        : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'

  return (
    <span
      className={[
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize',
        colorClasses,
      ].join(' ')}
    >
      {tier}
    </span>
  )
}

export function MlRiskScore({ score }: MlRiskBadgeProps) {
  if (score == null) {
    return <span className="text-xs text-muted-foreground">—</span>
  }
  return <span className="text-xs tabular-nums">{(score * 100).toFixed(1)}%</span>
}
