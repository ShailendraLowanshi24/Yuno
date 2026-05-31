import { useState, useEffect, useRef } from 'react'
import { agentApi } from '../api'
import { Spinner } from './ui'
import toast from 'react-hot-toast'
import { formatDistanceToNow } from 'date-fns'

export default function ChatPanel({ agent, sessionId, onSessionChange }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    if (!agent || !sessionId) return
    setLoadingHistory(true)
    agentApi.getMessages(agent.id, sessionId)
      .then(setMessages)
      .catch(() => {})
      .finally(() => setLoadingHistory(false))
  }, [agent?.id, sessionId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: input,
      created_at: new Date().toISOString(),
    }
    setMessages(m => [...m, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await agentApi.chat(agent.id, userMsg.content, sessionId)
      setMessages(m => [...m, {
        id: Date.now() + 1,
        role: 'assistant',
        content: res.response,
        created_at: new Date().toISOString(),
      }])
      if (res.session_id && res.session_id !== sessionId) {
        onSessionChange?.(res.session_id)
      }
    } catch (err) {
      toast.error('Failed to get response')
      setMessages(m => m.filter(msg => msg.id !== userMsg.id))
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!agent) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-600">
        Select an agent to start chatting
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-brand-600/20 border border-brand-600/40 flex items-center justify-center text-sm">
          🤖
        </div>
        <div>
          <div className="font-medium text-sm">{agent.name}</div>
          <div className="text-xs text-gray-500">{agent.role} · {sessionId?.slice(0, 8)}…</div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {loadingHistory ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : messages.length === 0 ? (
          <div className="text-center text-gray-600 py-8">
            <div className="text-3xl mb-2">💬</div>
            <div className="text-sm">Start a conversation with {agent.name}</div>
          </div>
        ) : messages.map(msg => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
        {loading && <TypingIndicator name={agent.name} />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={`Message ${agent.name}…`}
            rows={2}
            disabled={loading}
            className="input flex-1 resize-none text-sm"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="btn-primary px-4 self-end"
          >
            {loading ? <Spinner size="sm" /> : '↑'}
          </button>
        </div>
        <div className="text-xs text-gray-600 mt-1">Enter to send · Shift+Enter for newline</div>
      </div>
    </div>
  )
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 ${
        isUser ? 'bg-brand-600' : 'bg-gray-700'
      }`}>
        {isUser ? '👤' : '🤖'}
      </div>
      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        <div className={`px-3 py-2 rounded-xl text-sm whitespace-pre-wrap ${
          isUser
            ? 'bg-brand-600 text-white rounded-tr-none'
            : 'bg-gray-800 text-gray-100 rounded-tl-none'
        }`}>
          {msg.content}
        </div>
        <div className="text-xs text-gray-600">
          {formatDistanceToNow(new Date(msg.created_at), { addSuffix: true })}
        </div>
      </div>
    </div>
  )
}

function TypingIndicator({ name }) {
  return (
    <div className="flex gap-3">
      <div className="w-7 h-7 rounded-full bg-gray-700 flex items-center justify-center text-xs">🤖</div>
      <div className="bg-gray-800 px-3 py-2 rounded-xl rounded-tl-none">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map(i => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce"
              style={{ animationDelay: `${i * 150}ms` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
