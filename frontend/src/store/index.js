import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // ── Agents
  agents: [],
  setAgents: (agents) => set({ agents }),
  upsertAgent: (agent) => set(s => ({
    agents: s.agents.some(a => a.id === agent.id)
      ? s.agents.map(a => a.id === agent.id ? agent : a)
      : [agent, ...s.agents],
  })),
  removeAgent: (id) => set(s => ({ agents: s.agents.filter(a => a.id !== id) })),

  // ── Workflows
  workflows: [],
  setWorkflows: (workflows) => set({ workflows }),
  upsertWorkflow: (wf) => set(s => ({
    workflows: s.workflows.some(w => w.id === wf.id)
      ? s.workflows.map(w => w.id === wf.id ? wf : w)
      : [wf, ...s.workflows],
  })),
  removeWorkflow: (id) => set(s => ({ workflows: s.workflows.filter(w => w.id !== id) })),

  // ── Stats
  stats: null,
  setStats: (stats) => set({ stats }),

  // ── Live logs
  logs: [],
  addLog: (log) => set(s => ({ logs: [log, ...s.logs].slice(0, 500) })),
  clearLogs: () => set({ logs: [] }),
}))
