import { ArrowRight, CheckCircle2, ClipboardCheck, FileText, History, PlayCircle } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import StatusBadge from '../components/StatusBadge'

export default function DashboardPage({ runs, onConfigure, onOpenHistory }) {
  const completed = runs.filter(run => run.status === 'completed').length
  const active = runs.filter(run => ['queued', 'running'].includes(run.status)).length
  const recentRuns = runs.slice(0, 4)

  return <>
    <PageHeader eyebrow="Compliance workspace" title="Overview" description="Start a validation, track progress, and retrieve local evidence." icon={ClipboardCheck} />
    <section className="hero-panel">
      <div>
        <p className="eyebrow">Ready when you are</p>
        <h2>Validate your device against ICAF requirements.</h2>
        <p>Select a compliance clause, connect to the DUT, and keep all reports and evidence in this local workspace.</p>
        <button className="primary-button" onClick={onConfigure}><PlayCircle size={18} /> Configure a new check</button>
      </div>
      {/*<div className="hero-icon"><CheckCircle2 size={52} /></div>*/}
    </section>
    <section className="stat-grid" aria-label="Run summary">
      <StatCard label="Total runs" value={runs.length} icon={History} />
      <StatCard label="Completed" value={completed} icon={CheckCircle2} tone="success" />
      <StatCard label="In progress" value={active} icon={PlayCircle} tone="warning" />
    </section>
    <section className="panel recent-runs">
      <div className="panel-title panel-title-row"><div><h2>Recent checks</h2><p>Your most recent local compliance executions.</p></div><button className="text-button" onClick={onOpenHistory}>View all <ArrowRight size={15} /></button></div>
      {recentRuns.length === 0 ? <div className="empty-state"><FileText size={28} /><p>No checks have been run yet.</p><button className="text-button" onClick={onConfigure}>Configure your first check <ArrowRight size={15} /></button></div> : <div className="recent-run-list">{recentRuns.map(run => <div className="recent-run" key={run.id}><div><strong>{run.dut_host}</strong><span>Clause {run.clause} · {formatDate(run.created_at)}</span></div><StatusBadge status={run.status} /></div>)}</div>}
    </section>
  </>
}

function StatCard({ label, value, icon: Icon, tone = 'default' }) {
  return <article className={`stat-card ${tone}`}><div><span>{label}</span><strong>{value}</strong></div><Icon size={21} /></article>
}

function formatDate(value) { return value ? new Date(value).toLocaleDateString() : 'Not started' }
