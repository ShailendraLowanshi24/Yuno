import { useEffect, useState } from 'react'
import { monitorApi } from '../api'
import { useStore } from '../store'
import { useLiveLogs } from '../hooks/useLiveLogs'
import { StatCard, Badge, Spinner } from '../components/ui'
import { formatDistanceToNow } from 'date-fns'

const LEVEL_COLORS = {
  info:    'text-blue-400',
  warning: 'text-yellow-400',
  error:   'text-red-400',
  debug:   'text-gray-500',
}

const LEVEL_BG = {
  info:    'bg-blue-900/20',
  warning: 'bg-yellow-900/20',
  error:   'bg-red-900/20',
  debug:   'bg-gray-900/20',
}

export default function MonitorPage() {
  const { stats, setStats, logs } = useStore()
  const [filter, setFilter] = useState('all')
  const [messages, setMessages] = useState([])
  const [tab, setTab] = useState('logs')

  // Connect live log WebSocket
  useLiveLogs()

  useEffect(() => {
    monitorApi.getStats().then(setStats).catch(() => {})
    monitorApi.getMessages().then(setMessages).catch(() => {})
  }, [])

  const filteredLogs = filter === 'all'
    ? logs
    : logs.filter(l => l.level === filter)

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Monitor</h1>
        <p className="text-gray-400 mt-1">Real-time logs, agent messages, and token usage</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
        <StatCard label="Agents" value={stats?.agents ?? '—'} icon="🤖" />
        <StatCard label="Total Runs" value={stats?.total_runs ?? '—'} icon="▶️" color="text-green-400" />
        <StatCard label="Running" value={stats?.running_runs ?? '—'} icon="⚡" color="text-yellow-400" />
        <StatCard label="Tokens" value={stats ? fmtNum(stats.total_tokens) : '—'} icon="🧮" color="text-purple-400" />
        <StatCard label="Cost" value={stats ? `$${stats.total_cost_usd.toFixed(4)}` : '—'} icon="💰" color="text-orange-400" />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-900 rounded-lg p-1 w-fit mb-4">
        {['logs', 'messages'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded text-sm transition-colors capitalize ${
              tab === t ? 'bg-brand-600 text-white' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {t} {t === 'logs' && logs.length > 0 && (
              <span className="ml-1 bg-brand-500/30 text-brand-300 text-xs px-1.5 rounded-full">{logs.length}</span>
            )}
          </button>
        ))}
      </div>

      {tab === 'logs' && (
        <>
          {/* Filter bar */}
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs text-gray-500">Filter:</span>
            {['all', 'info', 'warning', 'error', 'debug'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-0.5 rounded text-xs transition-colors ${
                  filter === f
                    ? 'bg-brand-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {f}
              </button>
            ))}
            <div className="flex items-center gap-1.5 ml-auto">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs text-green-400">Live</span>
            </div>
          </div>

          {/* Log stream */}
          <div className="card overflow-hidden">
            <div className="bg-gray-950 font-mono text-xs max-h-[60vh] overflow-y-auto p-4 space-y-1">
              {filteredLogs.length === 0 ? (
                <div className="text-gray-600 text-center py-8">
                  Waiting for events… Run an agent or workflow to see logs here.
                </div>
              ) : (
                filteredLogs.map((log, i) => (
                  <LogLine key={log.id || i} log={log} />
                ))
              )}
            </div>
          </div>
        </>
      )}

      {tab === 'messages' && (
        <div className="card overflow-hidden">
          <div className="max-h-[60vh] overflow-y-auto divide-y divide-gray-800">
            {messages.length === 0 ? (
              <div className="text-gray-600 text-center py-8 text-sm">
                No messages yet. Start chatting with an agent.
              </div>
            ) : (
              messages.map(msg => (
                <div key={msg.id} className="p-3 hover:bg-gray-800/30 transition-colors">
                  <div className="flex items-center gap-3 mb-1">
                    <span className={`badge ${msg.role === 'user' ? 'bg-blue-900/40 text-blue-300' : 'bg-green-900/40 text-green-300'}`}>
                      {msg.role}
                    </span>
                    <span className="badge bg-gray-800 text-gray-400">{msg.channel}</span>
                    <span className="text-xs text-gray-600 ml-auto">
                      {formatDistanceToNow(new Date(msg.created_at), { addSuffix: true })}
                    </span>
                  </div>
                  <div className="text-sm text-gray-300 line-clamp-3">{msg.content}</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function LogLine({ log }) {
  const ts = log.timestamp
    ? new Date(log.timestamp).toLocaleTimeString('en', { hour12: false, fractionalSecondDigits: 3 })
    : '--:--:--'

  return (
    <div className={`flex gap-3 items-start px-2 py-0.5 rounded ${LEVEL_BG[log.level] || ''}`}>
      <span className="text-gray-600 shrink-0">{ts}</span>
      <span className={`shrink-0 w-16 ${LEVEL_COLORS[log.level] || 'text-gray-400'}`}>
        [{(log.level || 'info').toUpperCase()}]
      </span>
      <span className="text-gray-400 shrink-0 max-w-[100px] truncate">{log.event}</span>
      <span className="text-gray-200 flex-1">{log.message}</span>
      {log.tokens_used > 0 && (
        <span className="text-gray-600 shrink-0">{log.tokens_used}t</span>
      )}
    </div>
  )
}

function fmtNum(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}
