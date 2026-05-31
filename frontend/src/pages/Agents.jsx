import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { agentApi } from '../api'
import { useStore } from '../store'
import { SectionHeader, Badge, EmptyState, Spinner } from '../components/ui'
import AgentForm from '../components/AgentForm'
import toast from 'react-hot-toast'
import { formatDistanceToNow } from 'date-fns'

export default function AgentsPage() {
  const { agents, setAgents, upsertAgent, removeAgent } = useStore()
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)

  useEffect(() => {
    agentApi.list()
      .then(setAgents)
      .catch(() => toast.error('Failed to load agents'))
      .finally(() => setLoading(false))
  }, [])

  const handleDelete = async (agent) => {
    if (!confirm(`Delete agent "${agent.name}"?`)) return
    try {
      await agentApi.delete(agent.id)
      removeAgent(agent.id)
      toast.success('Agent deleted')
    } catch {
      toast.error('Delete failed')
    }
  }

  const openEdit = (agent) => { setEditing(agent); setShowForm(true) }
  const openCreate = () => { setEditing(null); setShowForm(true) }

  return (
    <div className="p-6">
      <SectionHeader
        title="Agents"
        subtitle="Create and manage your AI agents"
        action={
          <button onClick={openCreate} className="btn-primary">
            + New Agent
          </button>
        }
      />

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : agents.length === 0 ? (
        <EmptyState
          icon="🤖"
          title="No agents yet"
          description="Create your first AI agent to get started"
          action={<button onClick={openCreate} className="btn-primary">Create Agent</button>}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {agents.map(agent => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onEdit={() => openEdit(agent)}
              onDelete={() => handleDelete(agent)}
            />
          ))}
        </div>
      )}

      <AgentForm
        open={showForm}
        onClose={() => setShowForm(false)}
        initial={editing}
        onSaved={upsertAgent}
      />
    </div>
  )
}

function AgentCard({ agent, onEdit, onDelete }) {
  return (
    <div className="card p-4 hover:border-gray-700 transition-colors group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-600/20 border border-brand-600/30 flex items-center justify-center text-xl">
            🤖
          </div>
          <div>
            <div className="font-semibold text-white">{agent.name}</div>
            <div className="text-xs text-gray-500">{agent.role}</div>
          </div>
        </div>
        <Badge status={agent.status} />
      </div>

      <p className="text-xs text-gray-400 line-clamp-2 mb-3 min-h-[2rem]">
        {agent.system_prompt}
      </p>

      <div className="flex flex-wrap gap-1 mb-3">
        <span className="badge bg-gray-800 text-gray-400">{agent.model}</span>
        {agent.tools?.slice(0, 2).map(t => (
          <span key={t} className="badge bg-blue-900/40 text-blue-300">{t}</span>
        ))}
        {(agent.tools?.length ?? 0) > 2 && (
          <span className="badge bg-gray-800 text-gray-500">+{agent.tools.length - 2}</span>
        )}
        {agent.schedule && (
          <span className="badge bg-yellow-900/40 text-yellow-300">⏰ scheduled</span>
        )}
      </div>

      <div className="flex items-center justify-between pt-3 border-t border-gray-800">
        <span className="text-xs text-gray-600">
          {formatDistanceToNow(new Date(agent.created_at), { addSuffix: true })}
        </span>
        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Link to={`/agents/${agent.id}`} className="text-xs text-brand-400 hover:text-brand-300">Chat</Link>
          <button onClick={onEdit} className="text-xs text-gray-400 hover:text-gray-200">Edit</button>
          <button onClick={onDelete} className="text-xs text-red-400 hover:text-red-300">Delete</button>
        </div>
      </div>
    </div>
  )
}
