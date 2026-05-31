import { useState, useEffect } from 'react'
import { Modal, Input, Textarea, Select, Badge } from './ui'
import { agentApi } from '../api'
import toast from 'react-hot-toast'

const MODELS = [
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (fast, cheap)' },
  { value: 'gpt-4o', label: 'GPT-4o (powerful)' },
  { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
  { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku (fast)' },
]

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
]

const EMPTY = {
  name: '',
  role: '',
  system_prompt: '',
  model: 'gpt-4o-mini',
  provider: 'openai',
  tools: [],
  memory_enabled: true,
  memory_window: 20,
  max_tokens: 2048,
  temperature: 0.7,
  max_iterations: 10,
  schedule: '',
  schedule_prompt: '',
  guardrails: {},
}

export default function AgentForm({ open, onClose, initial, onSaved }) {
  const [form, setForm] = useState(EMPTY)
  const [availableTools, setAvailableTools] = useState([])
  const [saving, setSaving] = useState(false)
  const [tab, setTab] = useState('basic')

  useEffect(() => {
    agentApi.listTools().then(setAvailableTools).catch(() => {})
  }, [])

  useEffect(() => {
    if (initial) {
      setForm({
        ...EMPTY,
        ...initial,
        schedule: initial.schedule || '',
        schedule_prompt: initial.schedule_prompt || '',
      })
    } else {
      setForm(EMPTY)
    }
    setTab('basic')
  }, [initial, open])

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const toggleTool = (tool) => {
    set('tools', form.tools.includes(tool)
      ? form.tools.filter(t => t !== tool)
      : [...form.tools, tool])
  }

  const handleSave = async () => {
    if (!form.name.trim() || !form.role.trim() || !form.system_prompt.trim()) {
      toast.error('Name, role, and system prompt are required')
      return
    }
    setSaving(true)
    try {
      const payload = {
        ...form,
        schedule: form.schedule || null,
        schedule_prompt: form.schedule_prompt || null,
        temperature: parseFloat(form.temperature),
        max_tokens: parseInt(form.max_tokens),
        max_iterations: parseInt(form.max_iterations),
        memory_window: parseInt(form.memory_window),
      }
      let agent
      if (initial?.id) {
        agent = await agentApi.update(initial.id, payload)
        toast.success('Agent updated')
      } else {
        agent = await agentApi.create(payload)
        toast.success('Agent created')
      }
      onSaved(agent)
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const TABS = ['basic', 'tools', 'memory', 'schedule', 'guardrails']

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={initial ? 'Edit Agent' : 'Create Agent'}
      size="lg"
    >
      {/* Tab bar */}
      <div className="flex gap-1 mb-6 border-b border-gray-800 pb-0">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-sm capitalize rounded-t-lg transition-colors -mb-px border-b-2 ${
              tab === t
                ? 'text-brand-400 border-brand-500 font-medium'
                : 'text-gray-500 border-transparent hover:text-gray-300'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">

        {tab === 'basic' && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Input label="Agent Name *" value={form.name} onChange={v => set('name', v)} placeholder="e.g. Researcher" />
              <Input label="Role *" value={form.role} onChange={v => set('role', v)} placeholder="e.g. Research Specialist" />
            </div>
            <Textarea
              label="System Prompt *"
              value={form.system_prompt}
              onChange={v => set('system_prompt', v)}
              rows={6}
              placeholder="You are an expert research assistant..."
            />
            <div className="grid grid-cols-2 gap-4">
              <Select label="Provider" value={form.provider} onChange={v => set('provider', v)} options={PROVIDERS} />
              <Select label="Model" value={form.model} onChange={v => set('model', v)} options={MODELS} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Temperature ({form.temperature})</label>
                <input type="range" min="0" max="1" step="0.1" value={form.temperature}
                  onChange={e => set('temperature', e.target.value)}
                  className="w-full accent-brand-500" />
              </div>
              <Input label="Max Tokens" type="number" value={form.max_tokens} onChange={v => set('max_tokens', v)} />
            </div>
            <Input label="Max Iterations" type="number" value={form.max_iterations} onChange={v => set('max_iterations', v)} />
          </>
        )}

        {tab === 'tools' && (
          <>
            <p className="text-gray-400 text-sm">Select tools this agent can use during execution.</p>
            <div className="grid grid-cols-2 gap-2">
              {availableTools.map(tool => (
                <label
                  key={tool.name}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    form.tools.includes(tool.name)
                      ? 'border-brand-500 bg-brand-600/10'
                      : 'border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={form.tools.includes(tool.name)}
                    onChange={() => toggleTool(tool.name)}
                    className="mt-0.5 accent-brand-500"
                  />
                  <div>
                    <div className="text-sm font-medium text-gray-200">{tool.name}</div>
                    <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">{tool.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </>
        )}

        {tab === 'memory' && (
          <>
            <div className="flex items-center justify-between p-4 card">
              <div>
                <div className="font-medium">Enable Memory</div>
                <div className="text-sm text-gray-400">Agent remembers past messages in a session</div>
              </div>
              <button
                onClick={() => set('memory_enabled', !form.memory_enabled)}
                className={`relative w-12 h-6 rounded-full transition-colors ${form.memory_enabled ? 'bg-brand-600' : 'bg-gray-700'}`}
              >
                <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${form.memory_enabled ? 'translate-x-7' : 'translate-x-1'}`} />
              </button>
            </div>
            {form.memory_enabled && (
              <Input
                label="Memory Window (last N messages)"
                type="number"
                value={form.memory_window}
                onChange={v => set('memory_window', v)}
              />
            )}
          </>
        )}

        {tab === 'schedule' && (
          <>
            <Input
              label="Cron Schedule (optional)"
              value={form.schedule}
              onChange={v => set('schedule', v)}
              placeholder="*/30 * * * * (every 30 mins)"
            />
            <div className="text-xs text-gray-500 -mt-2">Format: minute hour day month weekday</div>
            <Textarea
              label="Scheduled Prompt"
              value={form.schedule_prompt}
              onChange={v => set('schedule_prompt', v)}
              rows={3}
              placeholder="Summarize today's top AI news..."
            />
          </>
        )}

        {tab === 'guardrails' && (
          <>
            <p className="text-gray-400 text-sm">Configure limits and safety rules for this agent.</p>
            <Input
              label="Max Response Length (words)"
              type="number"
              value={form.guardrails?.max_response_length || ''}
              onChange={v => set('guardrails', { ...form.guardrails, max_response_length: parseInt(v) || undefined })}
              placeholder="e.g. 500"
            />
            <div className="flex items-center justify-between p-4 card">
              <div>
                <div className="font-medium text-sm">Block Harmful Content</div>
                <div className="text-xs text-gray-400">Refuse requests that could cause harm</div>
              </div>
              <button
                onClick={() => set('guardrails', {
                  ...form.guardrails,
                  block_harmful: !form.guardrails?.block_harmful
                })}
                className={`relative w-12 h-6 rounded-full transition-colors ${form.guardrails?.block_harmful ? 'bg-brand-600' : 'bg-gray-700'}`}
              >
                <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${form.guardrails?.block_harmful ? 'translate-x-7' : 'translate-x-1'}`} />
              </button>
            </div>
          </>
        )}
      </div>

      <div className="flex gap-3 justify-end mt-6 pt-4 border-t border-gray-800">
        <button className="btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving…' : (initial ? 'Update Agent' : 'Create Agent')}
        </button>
      </div>
    </Modal>
  )
}
