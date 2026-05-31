import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { agentApi } from '../api'
import { Badge, Spinner, Modal, Input } from '../components/ui'
import ChatPanel from '../components/ChatPanel'
import AgentForm from '../components/AgentForm'
import { useStore } from '../store'
import toast from 'react-hot-toast'

export default function AgentDetail() {
  const { id } = useParams()
  const { upsertAgent } = useStore()
  const [agent, setAgent] = useState(null)
  const [sessions, setSessions] = useState([])
  const [sessionId, setSessionId] = useState(() => `session-${Date.now()}`)
  const [showEdit, setShowEdit] = useState(false)
  const [showChannel, setShowChannel] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    agentApi.get(id)
      .then(a => { setAgent(a); setLoading(false) })
      .catch(() => { toast.error('Agent not found'); setLoading(false) })

    agentApi.getSessions(id)
      .then(setSessions)
      .catch(() => {})
  }, [id])

  const handleSaved = (updated) => {
    setAgent(updated)
    upsertAgent(updated)
  }

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  if (!agent) return <div className="p-6 text-gray-400">Agent not found</div>

  return (
    <div className="flex h-full">
      {/* Left: Agent info + sessions */}
      <div className="w-64 border-r border-gray-800 flex flex-col">
        {/* Agent info */}
        <div className="p-4 border-b border-gray-800">
          <Link to="/agents" className="text-xs text-gray-500 hover:text-gray-300 mb-3 block">← Agents</Link>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-brand-600/20 border border-brand-600/30 flex items-center justify-center text-xl">🤖</div>
            <div>
              <div className="font-semibold">{agent.name}</div>
              <div className="text-xs text-gray-500">{agent.role}</div>
            </div>
          </div>
          <Badge status={agent.status} className="mb-3" />
          <div className="text-xs text-gray-500 mb-3 line-clamp-3">{agent.system_prompt}</div>
          <div className="flex gap-2">
            <button onClick={() => setShowEdit(true)} className="btn-secondary text-xs py-1 px-2 flex-1">Edit</button>
            <button onClick={() => setShowChannel(true)} className="btn-secondary text-xs py-1 px-2 flex-1">Channels</button>
          </div>
        </div>

        {/* Tools */}
        {agent.tools?.length > 0 && (
          <div className="p-4 border-b border-gray-800">
            <div className="text-xs text-gray-500 font-medium mb-2">TOOLS</div>
            <div className="flex flex-wrap gap-1">
              {agent.tools.map(t => (
                <span key={t} className="badge bg-blue-900/40 text-blue-300 text-xs">{t}</span>
              ))}
            </div>
          </div>
        )}

        {/* Sessions */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs text-gray-500 font-medium">SESSIONS</div>
            <button
              onClick={() => setSessionId(`session-${Date.now()}`)}
              className="text-xs text-brand-400 hover:text-brand-300"
            >
              + New
            </button>
          </div>
          <div className="space-y-1">
            {/* Current session (if not in list yet) */}
            {!sessions.includes(sessionId) && (
              <button
                className="w-full text-left px-2 py-1.5 rounded text-xs bg-brand-600/20 text-brand-300 border border-brand-600/30"
              >
                {sessionId.slice(0, 20)}… (new)
              </button>
            )}
            {sessions.map(s => (
              <button
                key={s}
                onClick={() => setSessionId(s)}
                className={`w-full text-left px-2 py-1.5 rounded text-xs transition-colors ${
                  s === sessionId
                    ? 'bg-brand-600/20 text-brand-300 border border-brand-600/30'
                    : 'text-gray-400 hover:bg-gray-800'
                }`}
              >
                {s.slice(0, 24)}…
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Right: Chat */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <ChatPanel
          agent={agent}
          sessionId={sessionId}
          onSessionChange={setSessionId}
        />
      </div>

      {/* Edit modal */}
      <AgentForm
        open={showEdit}
        onClose={() => setShowEdit(false)}
        initial={agent}
        onSaved={handleSaved}
      />

      {/* Channel config modal */}
      <ChannelModal
        open={showChannel}
        onClose={() => setShowChannel(false)}
        agent={agent}
      />
    </div>
  )
}

function ChannelModal({ open, onClose, agent }) {
  const [type, setType] = useState('telegram')
  const [botToken, setBotToken] = useState('')
  const [appToken, setAppToken] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      const config = type === 'telegram'
        ? { bot_token: botToken }
        : { bot_token: botToken, app_token: appToken }
      await agentApi.configureChannel(agent.id, type, config)
      toast.success(`${type} channel configured!`)
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to configure channel')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Configure Messaging Channel">
      <div className="space-y-4">
        <div>
          <label className="label">Channel Type</label>
          <select value={type} onChange={e => setType(e.target.value)} className="input">
            <option value="telegram">Telegram</option>
            <option value="slack">Slack</option>
          </select>
        </div>

        {type === 'telegram' && (
          <>
            <div className="bg-gray-800 rounded-lg p-3 text-xs text-gray-400">
              <strong className="text-gray-200">Setup:</strong> Message @BotFather on Telegram → /newbot → copy the token below.
            </div>
            <Input label="Bot Token" value={botToken} onChange={setBotToken} placeholder="7xxxxxxxxx:AAF..." />
          </>
        )}

        {type === 'slack' && (
          <>
            <div className="bg-gray-800 rounded-lg p-3 text-xs text-gray-400">
              <strong className="text-gray-200">Setup:</strong> Create a Slack App at api.slack.com. Enable Socket Mode. Add Bot Token Scopes: chat:write, im:history, im:read. Install to workspace.
            </div>
            <Input label="Bot Token (xoxb-...)" value={botToken} onChange={setBotToken} placeholder="xoxb-..." />
            <Input label="App Token (xapp-...)" value={appToken} onChange={setAppToken} placeholder="xapp-..." />
          </>
        )}

        <div className="flex gap-3 justify-end pt-2">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={handleSave} disabled={saving || !botToken}>
            {saving ? 'Connecting…' : 'Connect Channel'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
