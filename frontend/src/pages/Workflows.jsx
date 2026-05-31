import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { workflowApi } from '../api'
import { useStore } from '../store'
import { SectionHeader, Badge, EmptyState, Spinner, Modal } from '../components/ui'
import toast from 'react-hot-toast'
import { formatDistanceToNow } from 'date-fns'

export default function WorkflowsPage() {
  const navigate = useNavigate()
  const { workflows, setWorkflows, upsertWorkflow, removeWorkflow } = useStore()
  const [loading, setLoading] = useState(true)
  const [showTemplates, setShowTemplates] = useState(false)
  const [templates, setTemplates] = useState([])

  useEffect(() => {
    workflowApi.list()
      .then(setWorkflows)
      .catch(() => toast.error('Failed to load workflows'))
      .finally(() => setLoading(false))

    workflowApi.listTemplates().then(setTemplates).catch(() => {})
  }, [])

  const handleDelete = async (wf) => {
    if (!confirm(`Delete workflow "${wf.name}"?`)) return
    try {
      await workflowApi.delete(wf.id)
      removeWorkflow(wf.id)
      toast.success('Workflow deleted')
    } catch {
      toast.error('Delete failed')
    }
  }

  const handleCreateBlank = async () => {
    try {
      const wf = await workflowApi.create({ name: 'Untitled Workflow', nodes: [], edges: [] })
      upsertWorkflow(wf)
      navigate(`/workflows/${wf.id}`)
    } catch {
      toast.error('Failed to create workflow')
    }
  }

  const handleUseTemplate = async (key) => {
    try {
      const wf = await workflowApi.createFromTemplate(key)
      upsertWorkflow(wf)
      toast.success('Workflow created from template!')
      setShowTemplates(false)
      navigate(`/workflows/${wf.id}`)
    } catch {
      toast.error('Failed to create from template')
    }
  }

  return (
    <div className="p-6">
      <SectionHeader
        title="Workflows"
        subtitle="Build multi-agent pipelines with visual graph editor"
        action={
          <div className="flex gap-2">
            <button onClick={() => setShowTemplates(true)} className="btn-secondary">
              📋 Templates
            </button>
            <button onClick={handleCreateBlank} className="btn-primary">
              + New Workflow
            </button>
          </div>
        }
      />

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : workflows.length === 0 ? (
        <EmptyState
          icon="🔀"
          title="No workflows yet"
          description="Build a multi-agent pipeline or start from a template"
          action={
            <div className="flex gap-3">
              <button onClick={() => setShowTemplates(true)} className="btn-secondary">Use Template</button>
              <button onClick={handleCreateBlank} className="btn-primary">Create Blank</button>
            </div>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {workflows.map(wf => (
            <WorkflowCard key={wf.id} workflow={wf} onDelete={() => handleDelete(wf)} />
          ))}
        </div>
      )}

      {/* Templates Modal */}
      <Modal open={showTemplates} onClose={() => setShowTemplates(false)} title="Workflow Templates" size="lg">
        <p className="text-gray-400 text-sm mb-4">Pre-built multi-agent workflows ready to use.</p>
        <div className="space-y-3">
          {templates.map(tpl => (
            <div key={tpl.key} className="card p-4 hover:border-gray-700 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-medium text-white mb-1">{tpl.name}</div>
                  <p className="text-sm text-gray-400">{tpl.description}</p>
                  <div className="flex gap-2 mt-2">
                    {tpl.nodes?.filter(n => n.node_type !== 'input' && n.node_type !== 'output').map(n => (
                      <span key={n.id} className="badge bg-gray-800 text-gray-300">{n.label}</span>
                    ))}
                  </div>
                </div>
                <button
                  onClick={() => handleUseTemplate(tpl.key)}
                  className="btn-primary text-sm whitespace-nowrap"
                >
                  Use Template
                </button>
              </div>
            </div>
          ))}
        </div>
      </Modal>
    </div>
  )
}

function WorkflowCard({ workflow, onDelete }) {
  return (
    <div className="card p-4 hover:border-gray-700 transition-colors group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-600/20 border border-purple-600/30 flex items-center justify-center text-xl">🔀</div>
          <div>
            <div className="font-semibold text-white">{workflow.name}</div>
            {workflow.is_template && (
              <span className="text-xs text-yellow-400">📋 from template</span>
            )}
          </div>
        </div>
        <Badge status={workflow.status} />
      </div>

      {workflow.description && (
        <p className="text-xs text-gray-400 line-clamp-2 mb-3">{workflow.description}</p>
      )}

      <div className="flex gap-3 text-xs text-gray-500 mb-3">
        <span>📦 {workflow.nodes?.length ?? 0} nodes</span>
        <span>🔗 {workflow.edges?.length ?? 0} edges</span>
      </div>

      <div className="flex items-center justify-between pt-3 border-t border-gray-800">
        <span className="text-xs text-gray-600">
          {formatDistanceToNow(new Date(workflow.created_at), { addSuffix: true })}
        </span>
        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Link to={`/workflows/${workflow.id}`} className="text-xs text-brand-400 hover:text-brand-300">Open</Link>
          <button onClick={onDelete} className="text-xs text-red-400 hover:text-red-300">Delete</button>
        </div>
      </div>
    </div>
  )
}
