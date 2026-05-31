import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { monitorApi, agentApi, workflowApi } from '../api'
import { useStore } from '../store'
import { StatCard, Badge, Spinner } from '../components/ui'
import { formatDistanceToNow } from 'date-fns'

export default function Dashboard() {
  const { stats, setStats, agents, setAgents, workflows, setWorkflows } = useStore()

  useEffect(() => {
    monitorApi.getStats().then(setStats).catch(() => {})
    agentApi.list().then(setAgents).catch(() => {})
    workflowApi.list().then(setWorkflows).catch(() => {})
  }, [])

  return (
    <div className="p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">Platform overview and recent activity</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Agents" value={stats?.agents ?? '—'} icon="🤖" color="text-brand-400" />
        <StatCard label="Total Runs" value={stats?.total_runs ?? '—'} icon="▶️" color="text-green-400" />
        <StatCard label="Tokens Used" value={stats ? formatNum(stats.total_tokens) : '—'} icon="🧮" color="text-yellow-400" />
        <StatCard
          label="Total Cost"
          value={stats ? `$${stats.total_cost_usd.toFixed(4)}` : '—'}
          icon="💰"
          color="text-purple-400"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agents */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Agents</h2>
            <Link to="/agents" className="text-xs text-brand-400 hover:text-brand-300">View all →</Link>
          </div>
          {agents.length === 0 ? (
            <div className="text-gray-600 text-sm text-center py-4">No agents yet</div>
          ) : (
            <div className="space-y-2">
              {agents.slice(0, 5).map(a => (
                <Link
                  key={a.id}
                  to={`/agents/${a.id}`}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-base">🤖</span>
                    <div>
                      <div className="text-sm font-medium">{a.name}</div>
                      <div className="text-xs text-gray-500">{a.role}</div>
                    </div>
                  </div>
                  <Badge status={a.status} />
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Workflows */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Workflows</h2>
            <Link to="/workflows" className="text-xs text-brand-400 hover:text-brand-300">View all →</Link>
          </div>
          {workflows.length === 0 ? (
            <div className="text-gray-600 text-sm text-center py-4">No workflows yet</div>
          ) : (
            <div className="space-y-2">
              {workflows.slice(0, 5).map(w => (
                <Link
                  key={w.id}
                  to={`/workflows/${w.id}`}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-base">🔀</span>
                    <div>
                      <div className="text-sm font-medium">{w.name}</div>
                      <div className="text-xs text-gray-500">{w.nodes?.length ?? 0} nodes</div>
                    </div>
                  </div>
                  <Badge status={w.status} />
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recent Runs */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Recent Runs</h2>
            <Link to="/monitor" className="text-xs text-brand-400 hover:text-brand-300">Monitor →</Link>
          </div>
          {!stats?.recent_runs?.length ? (
            <div className="text-gray-600 text-sm text-center py-4">No runs yet</div>
          ) : (
            <div className="space-y-2">
              {stats.recent_runs.map(r => (
                <div key={r.id} className="flex items-center justify-between p-2 rounded-lg bg-gray-800/50">
                  <div>
                    <div className="text-xs font-mono text-gray-400">{r.id.slice(0, 8)}…</div>
                    <div className="text-xs text-gray-500">
                      {formatDistanceToNow(new Date(r.started_at), { addSuffix: true })}
                    </div>
                  </div>
                  <Badge status={r.status} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function formatNum(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}
