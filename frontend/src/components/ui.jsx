import { clsx } from 'clsx'

// ── Badge ─────────────────────────────────────

const STATUS_COLORS = {
  active: 'bg-green-900 text-green-300',
  idle: 'bg-gray-800 text-gray-400',
  running: 'bg-blue-900 text-blue-300',
  error: 'bg-red-900 text-red-300',
  disabled: 'bg-gray-800 text-gray-500',
  completed: 'bg-green-900 text-green-300',
  failed: 'bg-red-900 text-red-300',
  pending: 'bg-yellow-900 text-yellow-300',
  draft: 'bg-gray-800 text-gray-400',
  paused: 'bg-orange-900 text-orange-300',
}

export function Badge({ status, label, className }) {
  return (
    <span className={clsx('badge', STATUS_COLORS[status] || 'bg-gray-800 text-gray-300', className)}>
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
      {label || status}
    </span>
  )
}

// ── Spinner ───────────────────────────────────

export function Spinner({ size = 'md' }) {
  const s = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-10 h-10' }[size]
  return (
    <div className={clsx('animate-spin rounded-full border-2 border-gray-700 border-t-brand-500', s)} />
  )
}

// ── Modal ─────────────────────────────────────

export function Modal({ open, onClose, title, children, size = 'md' }) {
  if (!open) return null
  const widths = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-4xl' }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className={clsx('relative card p-6 w-full shadow-2xl', widths[size])}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-xl leading-none">✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ── Empty State ────────────────────────────────

export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-5xl mb-4">{icon}</div>
      <h3 className="text-lg font-medium text-gray-300 mb-1">{title}</h3>
      <p className="text-gray-500 text-sm mb-6 max-w-xs">{description}</p>
      {action}
    </div>
  )
}

// ── Section Header ─────────────────────────────

export function SectionHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
        {subtitle && <p className="text-gray-400 mt-1">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

// ── Select ─────────────────────────────────────

export function Select({ label, value, onChange, options, className }) {
  return (
    <div className={className}>
      {label && <label className="label">{label}</label>}
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="input"
      >
        {options.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  )
}

// ── Textarea ───────────────────────────────────

export function Textarea({ label, value, onChange, rows = 4, placeholder, className }) {
  return (
    <div className={className}>
      {label && <label className="label">{label}</label>}
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        rows={rows}
        placeholder={placeholder}
        className="input resize-none"
      />
    </div>
  )
}

// ── Input ──────────────────────────────────────

export function Input({ label, value, onChange, placeholder, type = 'text', className }) {
  return (
    <div className={className}>
      {label && <label className="label">{label}</label>}
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="input"
      />
    </div>
  )
}

// ── Stat Card ──────────────────────────────────

export function StatCard({ label, value, icon, color = 'text-brand-500', sub }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-3 mb-1">
        <span className={clsx('text-xl', color)}>{icon}</span>
        <span className="text-gray-400 text-sm">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
    </div>
  )
}
