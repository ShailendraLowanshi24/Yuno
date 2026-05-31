import { useEffect, useRef } from 'react'
import { useStore } from '../store'

export function useLiveLogs() {
  const addLog = useStore(s => s.addLog)
  const wsRef = useRef(null)

  useEffect(() => {
    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${protocol}://${window.location.host}/api/monitor/ws/logs`)
      wsRef.current = ws

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data)
          if (data.type !== 'ping') {
            addLog(data)
          }
        } catch {}
      }

      ws.onclose = () => {
        // Reconnect after 3 seconds
        setTimeout(connect, 3000)
      }

      ws.onerror = () => ws.close()
    }

    connect()
    return () => wsRef.current?.close()
  }, [addLog])
}
