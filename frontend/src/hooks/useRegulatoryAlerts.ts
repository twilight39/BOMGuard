import * as React from 'react'

export interface RegulatoryAlert {
  id: string
  type: string
  regulationId: string
  changesDetected: number
  substancesCreated: number
  substancesUpdated: number
  receivedAt: number
}

interface UseRegulatoryAlertsReturn {
  alerts: RegulatoryAlert[]
  dismissAlert: (id: string) => void
  connected: boolean
}

function getWsUrl(): string {
  const apiBase = import.meta.env.VITE_API_URL || ''
  if (apiBase) {
    const url = apiBase
      .replace(/^http:\/\//, 'ws://')
      .replace(/^https:\/\//, 'wss://')
    return `${url}/api/regulations/ws`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/regulations/ws`
}

export function useRegulatoryAlerts(): UseRegulatoryAlertsReturn {
  const [alerts, setAlerts] = React.useState<RegulatoryAlert[]>([])
  const [connected, setConnected] = React.useState(false)
  const wsRef = React.useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = React.useRef(0)

  const dismissAlert = React.useCallback((id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id))
  }, [])

  React.useEffect(() => {
    const wsUrl = getWsUrl()

    const connect = () => {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        reconnectAttempts.current = 0
      }

      ws.onclose = () => {
        setConnected(false)
        wsRef.current = null
        // Exponential backoff: max 30s
        const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000)
        reconnectAttempts.current += 1
        reconnectTimeoutRef.current = setTimeout(connect, delay)
      }

      ws.onerror = () => {
        // onclose will fire after this and handle reconnect
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'regulatory_change') {
            const alert: RegulatoryAlert = {
              id: `${data.regulation_id}-${Date.now()}`,
              type: data.type,
              regulationId: data.regulation_id,
              changesDetected: data.changes_detected,
              substancesCreated: data.substances_created,
              substancesUpdated: data.substances_updated,
              receivedAt: Date.now(),
            }
            setAlerts((prev) => [...prev, alert])
          }
        } catch {
          // ignore non-JSON messages
        }
      }
    }

    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  // Auto-dismiss alerts after 10 seconds
  React.useEffect(() => {
    if (alerts.length === 0) return
    const timer = setTimeout(() => {
      const cutoff = Date.now() - 10000
      setAlerts((prev) => prev.filter((a) => a.receivedAt > cutoff))
    }, 1000)
    return () => clearTimeout(timer)
  }, [alerts])

  return { alerts, dismissAlert, connected }
}
