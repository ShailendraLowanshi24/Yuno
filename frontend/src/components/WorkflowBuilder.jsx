import { useCallback, useState } from 'react'
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  addEdge,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { agentApi } from '../api'

// ── Custom node types ─────────────────────────

function AgentNode({ data, selected }) {
  const typeIcon = {
    agent: '🤖', agent_template: '🤖',
    input: '▶', output: '⬛',
    condition: '◆', tool: '🔧',
  }
  const typeBg = {
    agent: 'border-brand-500 bg-brand-600/10',
    agent_template: 'border-brand-500 bg-brand-600/10',
    input: 'border-green-500 bg-green-600/10',
    output: 'border-purple-500 bg-purple-600/10',
    condition: 'border-yellow-500 bg-yellow-600/10',
    tool: 'border-orange-500 bg-orange-600/10',
  }

  return (
    <div className={`
      px-4 py-3 rounded-xl border-2 min-w-[160px] cursor-pointer transition-all
      ${typeBg[data.node_type] || 'border-gray-600 bg-gray-800'}
      ${selected ? 'shadow-lg shadow-brand-500/20 scale-105' : ''}
    `}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{typeIcon[data.node_type] || '📦'}</span>
        <span className="font-semibold text-sm text-white truncate max-w-[120px]">{data.label}</span>
      </div>
      {data.agent_name && (
        <div className="text-xs text-gray-400 truncate">{data.agent_name}</div>
      )}
      {data.node_type === 'condition' && data.condition && (
        <div className="text-xs text-yellow-400 mt-1 font-mono truncate max-w-[140px]">
          if {data.condition}
        </div>
      )}
    </div>
  )
}

const NODE_TYPES = {
  agentNode: AgentNode,
}

const EDGE_STYLE = {
  stroke: '#4b5563',
  strokeWidth: 2,
}

// ── WorkflowBuilder ───────────────────────────

export default function WorkflowBuilder({ workflow, agents, onChange }) {
  // Convert DB format to React Flow format
  const toRFNodes = (wf) => (wf?.nodes || []).map(n => ({
    id: n.id,
    type: 'agentNode',
    position: n.position || { x: 0, y: 0 },
    data: {
      label: n.label,
      node_type: n.node_type,
      agent_id: n.agent_id,
      agent_name: agents.find(a => a.id === n.agent_id)?.name,
      config: n.config || {},
    },
  }))

  const toRFEdges = (wf) => (wf?.edges || []).map(e => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    condition: e.condition,
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' },
    style: EDGE_STYLE,
    labelStyle: { fill: '#9ca3af', fontSize: 11 },
    labelBgStyle: { fill: '#1f2937' },
  }))

  const [nodes, setNodes, onNodesChange] = useNodesState(toRFNodes(workflow))
  const [edges, setEdges, onEdgesChange] = useEdgesState(toRFEdges(workflow))
  const [selectedNode, setSelectedNode] = useState(null)
  const [nodeConfig, setNodeConfig] = useState({})

  const onConnect = useCallback((params) => {
    const edge = {
      ...params,
      markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' },
      style: EDGE_STYLE,
    }
    setEdges(eds => addEdge(edge, eds))
    syncBack()
  }, [setEdges])

  const syncBack = useCallback(() => {
    // Persist graph changes back to parent
    if (onChange) {
      onChange({
        nodes: nodes.map(n => ({
          id: n.id,
          node_type: n.data.node_type,
          label: n.data.label,
          agent_id: n.data.agent_id,
          position: n.position,
          config: n.data.config || {},
        })),
        edges: edges.map(e => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label,
          condition: e.condition,
        })),
      })
    }
  }, [nodes, edges, onChange])

  const addNode = (type) => {
    const id = `node-${Date.now()}`
    const labels = {
      agent: 'New Agent', input: 'Input', output: 'Output', condition: 'Condition'
    }
    const newNode = {
      id,
      type: 'agentNode',
      position: { x: 200 + Math.random() * 200, y: 200 + Math.random() * 100 },
      data: { label: labels[type] || 'Node', node_type: type, config: {} },
    }
    setNodes(ns => [...ns, newNode])
  }

  const updateSelectedNode = (key, value) => {
    if (!selectedNode) return
    setNodes(ns => ns.map(n => {
      if (n.id !== selectedNode.id) return n
      return {
        ...n,
        data: {
          ...n.data,
          [key]: value,
          agent_name: key === 'agent_id'
            ? agents.find(a => a.id === value)?.name
            : n.data.agent_name,
        },
      }
    }))
  }

  const onNodeClick = (_, node) => setSelectedNode(node)
  const onPaneClick = () => setSelectedNode(null)

  return (
    <div className="flex h-full">
      {/* Canvas */}
      <div className="flex-1 relative">
        {/* Toolbar */}
        <div className="absolute top-3 left-3 z-10 flex gap-2">
          {['agent', 'input', 'output', 'condition'].map(type => (
            <button
              key={type}
              onClick={() => addNode(type)}
              className="btn-secondary text-xs py-1 px-2"
            >
              + {type}
            </button>
          ))}
        </div>

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={NODE_TYPES}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} color="#1f2937" gap={20} />
          <Controls />
          <MiniMap
            nodeColor={(n) => {
              const colors = {
                agent: '#4f63d2', agent_template: '#4f63d2',
                input: '#10b981', output: '#8b5cf6',
                condition: '#f59e0b',
              }
              return colors[n.data?.node_type] || '#374151'
            }}
            maskColor="rgba(0,0,0,0.6)"
          />
        </ReactFlow>
      </div>

      {/* Node config panel */}
      {selectedNode && (
        <div className="w-64 bg-gray-900 border-l border-gray-800 p-4 overflow-y-auto">
          <h3 className="font-semibold mb-4 flex items-center justify-between">
            Node Config
            <button onClick={() => setSelectedNode(null)} className="text-gray-500 text-sm">✕</button>
          </h3>

          <div className="space-y-3">
            <div>
              <label className="label">Label</label>
              <input
                value={selectedNode.data.label}
                onChange={e => updateSelectedNode('label', e.target.value)}
                className="input text-sm"
              />
            </div>

            <div>
              <label className="label">Node Type</label>
              <select
                value={selectedNode.data.node_type}
                onChange={e => updateSelectedNode('node_type', e.target.value)}
                className="input text-sm"
              >
                {['agent', 'input', 'output', 'condition'].map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            {selectedNode.data.node_type === 'agent' && (
              <div>
                <label className="label">Assign Agent</label>
                <select
                  value={selectedNode.data.agent_id || ''}
                  onChange={e => updateSelectedNode('agent_id', e.target.value)}
                  className="input text-sm"
                >
                  <option value="">— select agent —</option>
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>
            )}

            {selectedNode.data.node_type === 'condition' && (
              <div>
                <label className="label">Condition Expression</label>
                <textarea
                  value={selectedNode.data.config?.condition || ''}
                  onChange={e => updateSelectedNode('config', {
                    ...selectedNode.data.config,
                    condition: e.target.value,
                  })}
                  rows={3}
                  placeholder="state.get('approved', False)"
                  className="input text-xs font-mono resize-none"
                />
              </div>
            )}

            <button
              onClick={syncBack}
              className="btn-primary w-full text-sm"
            >
              Apply Changes
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
