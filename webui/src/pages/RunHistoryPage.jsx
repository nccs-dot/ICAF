import { useEffect, useState } from 'react'
import { ArrowLeft, CheckCircle2, ChevronRight, Clock, Download, ExternalLink, FileText, History, LoaderCircle, Monitor, ShieldCheck, Terminal, XCircle } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import StatusBadge from '../components/StatusBadge'

export default function RunHistoryPage({ runs, selectedRun, onOpen, onClose }) {
  if (selectedRun) {
    return <RunDetailPage run={selectedRun} onBack={onClose} />
  }

  return (
    <>
      <PageHeader 
        eyebrow="Local evidence archive" 
        title="Run history" 
        description="Reports, logs, and screenshots from previous executions." 
        icon={History} 
      />
      <section className="panel">
        <div className="panel-title">
          <div>
            <h2>All checks</h2>
            <p>{runs.length} recorded execution{runs.length === 1 ? '' : 's'}</p>
          </div>
        </div>
        {runs.length === 0 ? (
          <div className="empty-state">
            <FileText size={28} />
            <p>No runs yet.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>DUT Host</th>
                  <th>Clause</th>
                  <th>Status</th>
                  <th>Started</th>
                  <th><span className="sr-only">Open details</span></th>
                </tr>
              </thead>
              <tbody>
                {runs.map(run => (
                  <tr key={run.id} onClick={() => onOpen(run)}>
                    <td><strong>{run.id.slice(0, 8)}</strong></td>
                    <td>{run.dut_host}<small>{run.profile}</small></td>
                    <td>{run.clause}</td>
                    <td><StatusBadge status={run.status} /></td>
                    <td>{formatDate(run.started_at || run.created_at)}</td>
                    <td><ChevronRight size={18} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}

function RunDetailPage({ run, onBack }) {
  const [logText, setLogText] = useState('')
  const [loadingLog, setLoadingLog] = useState(false)

  const reports = run.evidence?.filter(item => item.kind === 'report') || []
  const shots = run.evidence?.filter(item => item.kind === 'screenshot') || []
  const logs = run.evidence?.filter(item => item.kind === 'log') || []
  const url = item => `/api/runs/${run.id}/artifacts/${item.relative_path}`

  useEffect(() => {
    if (logs.length === 0) {
      setLogText('')
      return
    }
    setLoadingLog(true)
    fetch(url(logs[0]))
      .then(res => {
        if (!res.ok) throw new Error('Failed to load log file')
        return res.text()
      })
      .then(text => setLogText(text))
      .catch(err => setLogText(`[Could not load logs: ${err.message}]`))
      .finally(() => setLoadingLog(false))
  }, [run.id, logs.length])

  return (
    <>
      <div style={{ marginBottom: 20 }}>
        <button 
          type="button" 
          onClick={onBack}
          className="secondary-button"
          style={{ cursor: 'pointer' }}
        >
          <ArrowLeft size={16} /> Back to all runs
        </button>
      </div>

      <div className="page-header">
        <div>
          <p className="eyebrow">Execution Summary</p>
          <h1>Run {run.id.slice(0, 8)} - {run.dut_host}</h1>
          <p>Clause {run.clause} | Profile: {run.profile}</p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <StatusBadge status={run.status} />
          {reports.map(item => (
            <a key={item.id} className="primary-button" href={url(item)} download>
              <Download size={16} /> Download Report
            </a>
          ))}
        </div>
      </div>

      {run.error_message && (
        <div className="error-message" style={{ marginBottom: 20 }}>
          <XCircle size={18} />
          <div>
            <strong>Execution Error:</strong> {run.error_message}
          </div>
        </div>
      )}

      {/* Metadata Metrics Row */}
      <div className="form-grid" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', padding: 0, gap: 14, marginBottom: 24 }}>
        <div className="panel" style={{ padding: '14px 18px' }}>
          <span style={{ color: '#64748b', fontSize: 11, fontWeight: 700, textTransform: 'uppercase' }}>Target Host</span>
          <h3 style={{ margin: '4px 0 0', fontSize: 15 }}>{run.dut_host}</h3>
        </div>
        <div className="panel" style={{ padding: '14px 18px' }}>
          <span style={{ color: '#64748b', fontSize: 11, fontWeight: 700, textTransform: 'uppercase' }}>Clause</span>
          <h3 style={{ margin: '4px 0 0', fontSize: 15 }}>{run.clause}</h3>
        </div>
        <div className="panel" style={{ padding: '14px 18px' }}>
          <span style={{ color: '#64748b', fontSize: 11, fontWeight: 700, textTransform: 'uppercase' }}>Started</span>
          <h3 style={{ margin: '4px 0 0', fontSize: 13, fontWeight: 600 }}>{formatDate(run.started_at || run.created_at)}</h3>
        </div>
        <div className="panel" style={{ padding: '14px 18px' }}>
          <span style={{ color: '#64748b', fontSize: 11, fontWeight: 700, textTransform: 'uppercase' }}>Finished</span>
          <h3 style={{ margin: '4px 0 0', fontSize: 13, fontWeight: 600 }}>{formatDate(run.finished_at)}</h3>
        </div>
      </div>

      {/* Two-Column Wide Split Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 20, alignItems: 'start' }}>
        
        {/* Left Column: Terminal / Logs */}
        <section className="panel">
          <div className="panel-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2>Execution Log</h2>
              <p>Terminal output and real-time execution steps</p>
            </div>
            {logs[0] && (
              <a className="text-download" href={url(logs[0])} download>
                <Download size={14} /> Download Raw Log
              </a>
            )}
          </div>
          <div style={{ padding: 18 }}>
            {loadingLog ? (
              <div style={{ padding: '30px 0', textAlign: 'center', color: '#64748b' }}>
                <LoaderCircle className="spin" size={18} style={{ verticalAlign: 'middle', marginRight: 8 }} />
                Loading execution log...
              </div>
            ) : logText ? (
              <pre style={{
                background: '#0f172a',
                color: '#f1f5f9',
                padding: 16,
                borderRadius: 0,
                fontSize: 12,
                lineHeight: 1.5,
                maxHeight: 520,
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
                margin: 0,
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace'
              }}>
                <code>{logText}</code>
              </pre>
            ) : (
              <p className="muted">
                {run.status === 'running' 
                  ? 'Execution in progress. Logs will populate once completed.' 
                  : 'No logs available for this execution.'}
              </p>
            )}
          </div>
        </section>

        {/* Right Column: Screenshots & Artifacts */}
        <div style={{ display: 'grid', gap: 20 }}>
          <section className="panel">
            <div className="panel-title">
              <div>
                <h2>Screenshots & Captures</h2>
                <p>{shots.length} captured visual evidence item{shots.length === 1 ? '' : 's'}</p>
              </div>
            </div>
            <div style={{ padding: 18 }}>
              {shots.length === 0 ? (
                <p className="muted">
                  {run.status === 'completed' 
                    ? 'No screenshots were generated for this run.' 
                    : 'Screenshots appear when the run completes.'}
                </p>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
                  {shots.map(item => (
                    <a 
                      href={url(item)} 
                      key={item.id} 
                      target="_blank" 
                      rel="noreferrer"
                      style={{ 
                        textDecoration: 'none', 
                        border: '1px solid #e2e8f0', 
                        padding: 8, 
                        background: '#fafbfc',
                        color: '#0f172a',
                        fontSize: 12
                      }}
                    >
                      <img 
                        src={url(item)} 
                        alt={item.label} 
                        style={{ 
                          width: '100%', 
                          aspectRatio: '16/10', 
                          objectFit: 'cover', 
                          border: '1px solid #e2e8f0',
                          marginBottom: 6,
                          display: 'block'
                        }} 
                      />
                      <span style={{ fontWeight: 600, display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {item.label}
                      </span>
                      <span style={{ color: '#005ea2', fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
                        <ExternalLink size={12} /> View original
                      </span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          </section>

          {reports.length > 0 && (
            <section className="panel">
              <div className="panel-title">
                <div>
                  <h2>Generated Reports</h2>
                  <p>Audit and compliance verification documents</p>
                </div>
              </div>
              <div style={{ padding: 18, display: 'grid', gap: 10 }}>
                {reports.map(item => (
                  <div 
                    key={item.id} 
                    style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      border: '1px solid #e2e8f0', 
                      padding: '12px 16px',
                      background: '#fafafa'
                    }}
                  >
                    <div>
                      <strong style={{ display: 'block', fontSize: 13 }}>{item.label}</strong>
                      <small style={{ color: '#64748b' }}>{item.relative_path}</small>
                    </div>
                    <a className="secondary-button" href={url(item)} download>
                      <Download size={14} /> Download PDF
                    </a>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

      </div>
    </>
  )
}

function formatDate(value) { 
  return value ? new Date(value).toLocaleString() : 'Not started' 
}