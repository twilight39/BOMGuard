import { useMemo } from 'react'
import { themeBalham, colorSchemeLight, colorSchemeDark } from 'ag-grid-community'
import { useTheme } from '@/contexts/ThemeContext'

export function useAgGridTheme() {
  const { resolvedTheme } = useTheme()
  return useMemo(
    () =>
      resolvedTheme === 'dark'
        ? themeBalham.withPart(colorSchemeDark)
        : themeBalham.withPart(colorSchemeLight),
    [resolvedTheme]
  )
}
