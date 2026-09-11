import { ClipboardCheck, History, LayoutDashboard, ShieldCheck } from 'lucide-react'

const navigation = [
  { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
  { id: 'configure', label: 'New check', icon: ClipboardCheck },
  { id: 'history', label: 'Run history', icon: History },
]

export default function AppLayout({ activePage, children, onNavigate, runCount }) {
  return <div className="app-shell">
    <header className="top-header">
      <div className="header-container">
        <button className="brand-group" onClick={() => onNavigate('dashboard')} aria-label="Go to overview">
          <span className="brand"><ShieldCheck className="brand-icon" size={22} /> ICAF</span>
          <span className="brand-divider">/</span>
          <span className="brand-subtitle">Compliance Suite</span>
        </button>
        <nav className="tab-nav" aria-label="Primary navigation">
          {navigation.map(({ id, label, icon: Icon }) => <button key={id} className={`nav-tab ${activePage === id ? 'active' : ''}`} onClick={() => onNavigate(id)}>
            <Icon size={16} />
            <span>{label}</span>
            {id === 'history' && runCount > 0 && <span className="tab-badge">{runCount}</span>}
          </button>)}
        </nav>
        <div className="header-status"><span className="local-dot" /> Local workspace</div>
      </div>
    </header>
    <main className="content">{children}</main>
  </div>
}
