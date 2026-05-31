import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// ─── Agents ───────────────────────────────────
export const agentApi = {
  list: () => api.get('/agents/').then(r => r.data),
  create: (data) => api.post('/agents/', data).then(r => r.data),
  get: (id) => api.get(`/agents/${id}`).then(r => r.data),
  update: (id, data) => api.put(`/agents/${id}`, data).then(r => r.data),
  delete: (id) => api.delete(`/agents/${id}`),
  chat: (id, message, sessionId) =>
    api.post(`/agents/${id}/chat`, { message, session_id: sessionId }).then(r => r.data),
  getMessages: (id, sessionId) =>
    api.get(`/agents/${id}/messages/${sessionId}`).then(r => r.data),
  getSessions: (id) => api.get(`/agents/${id}/sessions`).then(r => r.data),
  listTools: () => api.get('/agents/tools').then(r => r.data),
  configureChannel: (id, channelType, config) =>
    api.post(`/agents/${id}/channels`, { channel_type: channelType, config }).then(r => r.data),
  removeChannel: (id, channelType) =>
    api.delete(`/agents/${id}/channels/${channelType}`).then(r => r.data),
}

// ─── Workflows ────────────────────────────────
export const workflowApi = {
  list: () => api.get('/workflows/').then(r => r.data),
  create: (data) => api.post('/workflows/', data).then(r => r.data),
  get: (id) => api.get(`/workflows/${id}`).then(r => r.data),
  update: (id, data) => api.put(`/workflows/${id}`, data).then(r => r.data),
  delete: (id) => api.delete(`/workflows/${id}`),
  listTemplates: () => api.get('/workflows/templates').then(r => r.data),
  createFromTemplate: (key) => api.post(`/workflows/templates/${key}`).then(r => r.data),
  run: (id, input, trigger = 'manual') =>
    api.post(`/workflows/${id}/run`, { input, trigger }).then(r => r.data),
  getRuns: (id) => api.get(`/workflows/${id}/runs`).then(r => r.data),
  getRun: (runId) => api.get(`/workflows/runs/${runId}`).then(r => r.data),
  getRunLogs: (runId) => api.get(`/workflows/runs/${runId}/logs`).then(r => r.data),
}

// ─── Monitor ──────────────────────────────────
export const monitorApi = {
  getStats: () => api.get('/monitor/stats').then(r => r.data),
  getLogs: (params) => api.get('/monitor/logs', { params }).then(r => r.data),
  getMessages: () => api.get('/monitor/messages').then(r => r.data),
}

export default api
