import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { workflowApi, agentApi } from '../api'
import { useStore } from '../store'
import { Badge, Spinner, Modal } from '../components/ui'
import WorkflowBuilder from '../components/WorkflowBuilder'
import toast from 'react-hot-toast'
import { formatDistanceToNow } from 'date-fns'

export default function WorkflowDetail() {
  const { id } = useParams()
  const { upsertWorkflow } = useStore()
  const [workflow, setWorkflow] = useState(null)
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [runs, setRuns] = useState([])
  const [showRun, setShowRun] = useState(false)
  const [runInput, setRunInput] = useState('')
  const [running, setRunning] = useState(false)
  const [activeRun, setActiveRun] = useState(null)
  const [runLogs, setRunLogs] = useState([])
  const [pendingGraph, setPendingGraph] = useState(null)
  const [tab, setTab] = useState('builder')

  useEffect(() => {
    Promise.all([
      workflowApi.get(id),
      agentApi.list(),
      workflowApi.getRuns(id),
    ]).then(([wf, ags, rs]) => {
      setWorkflow(wf)
      setAgents(ags)
      setRuns(rs)
    }).catch(() => toast.error('Failed to load workflow'))
      .finally(() => setLoading(false))
  }, [id])

  const handleGraphChange = useCallback((graph) => {
    setPendingGraph(graph)
  }, [])

  const handleSave = async () => {
    if (!pendingGraph && !workflow) return
    setSaving(true)
    try {
      const payload = pendingGraph
        ? {
            name: workflow.name,
            description: workflow.description,
            nodes: pendingGraph.nodes,
            edges: pendingGraph.edges,
          }
        : { name: workflow.name }

      const updated = await workflowApi.update(id, payload)
      setWorkflow(updated)
      upsertWorkflow(updated)
      setPendingGraph(null)
      toast.success('Workflow saved')
    } catch {
      toast.error('Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleRun = async () => {
    if (!runInput.trim()) return
    setRunning(true)
    try {
      const run = await workflowApi.run(id, runInput)
      setActiveRun(run)
      setRuns(rs => [run, ...rs])
      setShowRun(false)
      setRunInput('')
      toast.success('Workflow started!')
      setTab('runs')
      // Poll for completion
      pollRun(run.id)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to start workflow')
    } finally {
      setRunning(false)
    }
  }

  const pollRun = async (runId) => {
    const interval = setInterval(async () => {
      try {
        const run = await workflowApi.getRun(runId)
        setRuns(rs => rs.map(r => r.id === runId ? run : r))
        if (run.id === activeRun?.id) setActiveRun(run)

        if (['completed', 'failed', 'cancelled'].includes(run.status)) {
          clearInterval(interval)
          const logs = await workflowApi.getRunLogs(runId)
          setRunLogs(logs)
        }
      } catch {
        clearInterval(interval)
      }
    }, 1500)
  }

  const viewRunLogs = async (run) => {
    setActiveRun(run)
    setTab('runs')
    const logs = await workflowApi.getRunLogs(run.id).catch(() => [])
    setRunLogs(logs)
  }

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  if (!workflow) return <div className="p-6 text-gray-400">Workflow not found</div>

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center gap-4 px-4 py-3 border-b border-gray-800 shrink-0">
        <Link to="/workflows" className="text-gray-500 hover:text-gray-300 text-sm">← Workflows</Link>
        <div className="flex-1">
          <h1 className="font-semibold">{workflow.name}</h1>
          <div className="text-xs text-gray-500">{workflow.nodes?.length} nodes · {workflow.edges?.length} edges</div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-gray-900 rounded-lg p-1">
          {['builder', 'runs'].map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1 rounded text-sm transition-colors capitalize ${
                tab === t ? 'bg-brand-600 text-white' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {pendingGraph && (
          <button onClick={handleSave} disabled={saving} className="btn-secondary text-sm">
            {saving ? 'Saving…' : '💾 Save'}
          </button>
        )}
        <button onClick={() => setShowRun(true)} className="btn-primary text-sm">
          ▶ Run Workflow
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {tab === 'builder' && (
          <WorkflowBuilder
            workflow={workflow}
            agents={agents}
            onChange={handleGraphChange}
          />
        )}

        {tab === 'runs' && (
          <div className="flex h-full">
            {/* Runs list */}
            <div className="w-72 border-r border-gray-800 overflow-y-auto p-4">
              <h3 className="text-sm font-medium text-gray-400 mb-3">Run History</h3>
              {runs.length === 0 ? (
                <div className="text-gray-600 text-sm text-center py-8">No runs yet</div>
              ) : (
                <div className="space-y-2">
                  {runs.map(run => (
                    <button
                      key={run.id}
                      onClick={() => viewRunLogs(run)}
                      className={`w-full text-left p-3 rounded-lg border transition-colors ${
                        activeRun?.id === run.id
                          ? 'border-brand-500 bg-brand-600/10'
                          : 'border-gray-800 hover:border-gray-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-mono text-gray-400">{run.id.slice(0, 8)}…</span>
                        <Badge status={run.status} />
                      </div>
                      <div className="text-xs text-gray-500">
                        {formatDistanceToNow(new Date(run.started_at), { addSuffix: true })}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Run detail */}
            <div className="flex-1 p-4 overflow-y-auto">
              {activeRun ? (
                <RunDetail run={activeRun} logs={runLogs} />
              ) : (
                <div className="text-gray-600 text-center py-16">Select a run to view details</div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Run input modal */}
      <Modal open={showRun} onClose={() => setShowRun(false)} title="Run Workflow">
        <div className="space-y-4">
          <div>
            <label className="label">Input / Initial Prompt</label>
            <textarea
              value={runInput}
              onChange={e => setRunInput(e.target.value)}
              rows={4}
              placeholder="What should the agents work on?"
              className="input resize-none"
            />
          </div>
          <div className="flex gap-3 justify-end">
            <button className="btn-secondary" onClick={() => setShowRun(false)}>Cancel</button>
            <button
              className="btn-primary"
              onClick={handleRun}
              disabled={running || !runInput.trim()}
            >
              {running ? 'Starting…' : '▶ Start Run'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

function RunDetail({ run, logs }) {
  return (
    <div className="space-y-4 max-w-3xl">
      {/* Status */}
      <div className="card p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <Badge status={run.status} label={run.status.toUpperCase()} />
          <span className="text-sm text-gray-400">Trigger: {run.trigger}</span>
          <span className="text-sm text-gray-400">
            Started: {new Date(run.started_at).toLocaleTimeString()}
          </span>
          {run.completed_at && (
            <span className="text-sm text-gray-400">
              Completed: {new Date(run.completed_at).toLocaleTimeString()}
            </span>
          )}
        </div>
        {run.total_tokens > 0 && (
          <div className="mt-2 flex gap-4 text-xs text-gray-500">
            <span>🧮 {run.total_tokens.toLocaleString()} tokens</span>
            <span>💰 ${run.total_cost?.toFixed(6) || '0.000000'}</span>
          </div>
        )}
      </div>

      {/* Output */}
      {run.output_data?.result && (
        <div className="card p-4">
          <div className="text-xs font-medium text-gray-400 mb-2">OUTPUT</div>
          <div className="text-sm text-gray-200 whitespace-pre-wrap font-mono bg-gray-950 rounded-lg p-3">
            {run.output_data.result}
          </div>
        </div>
      )}

      {/* Error */}
      {run.error && (
        <div className="card p-4 border-red-800">
          <div className="text-xs font-medium text-red-400 mb-2">ERROR</div>
          <div className="text-sm text-red-300 font-mono">{run.error}</div>
        </div>
      )}

      {/* Logs */}
      {logs.length > 0 && (
        <div className="card p-4">
          <div className="text-xs font-medium text-gray-400 mb-3">EXECUTION LOGS ({logs.length})</div>
          <div className="space-y-1.5 font-mono text-xs max-h-80 overflow-y-auto">
            {logs.map(log => (
              <div key={log.id} className="flex gap-3 items-start">
                <span className={`shrink-0 ${
                  log.level === 'error' ? 'text-red-400' :
                  log.level === 'warning' ? 'text-yellow-400' : 'text-gray-500'
                }`}>
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className={`shrink-0 w-14 ${
                  log.level === 'error' ? 'text-red-400' :
                  log.level === 'warning' ? 'text-yellow-400' : 'text-green-400'
                }`}>
                  [{log.level.toUpperCase()}]
                </span>
                <span className="text-gray-300">{log.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
