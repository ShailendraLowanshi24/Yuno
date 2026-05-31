import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'

const NAV = [
  { to: '/',           icon: '📊', label: 'Dashboard' },
  { to: '/agents',     icon: '🤖', label: 'Agents' },
  { to: '/workflows',  icon: '🔀', label: 'Workflows' },
  { to: '/monitor',    icon: '📡', label: 'Monitor' },
]

export default function Sidebar() {
  return (
    <aside className="w-56 min-h-screen bg-gray-950 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🤖</span>
          <div>
            <div className="font-bold text-white leading-tight">Yuno AI</div>
            <div className="text-xs text-gray-500">Agent Platform</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        {NAV.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) => clsx(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              isActive
                ? 'bg-brand-600/20 text-brand-400 border border-brand-600/30'
                : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
            )}
          >
            <span className="text-base">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800">
        <div className="text-xs text-gray-600">v1.0.0 · LangGraph Runtime</div>
      </div>
    </aside>
  )
}
