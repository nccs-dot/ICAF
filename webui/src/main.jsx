import { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import AppLayout from './components/AppLayout'
import ConfigurePage from './pages/ConfigurePage'
import DashboardPage from './pages/DashboardPage'
import RunHistoryPage from './pages/RunHistoryPage'
import './styles.css'

const initialForm = {
  clause: '1.6.5',
  profile: 'default',
  ssh_ip: '10.80.127.211',
  ssh_user: 'dut',
  ssh_password: '',
  snmp_user: 'snmpuser',
  snmp_auth_pass: '',
  snmp_priv_pass: '',
  snmp_community: 'community',
  web_login_url: '',
  web_username: 'admin',
  web_password: '',
}

function App() {
  const [page, setPage] = useState('dashboard')
  const [form, setForm] = useState(initialForm)
  const [oamFile, setOamFile] = useState(null)
  const [config, setConfig] = useState({ clauses: {}, profiles: ['default'] })
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const refreshRuns = async () => {
    try {
      const response = await fetch('/api/runs')
      if (response.ok) setRuns(await response.json())
    } catch {
      // The interface remains usable while the local API is unavailable.
    }
  }

  useEffect(() => {
    fetch('/api/configuration')
      .then(response => response.json())
      .then(data => {
        setConfig(data)
        if (data.profiles?.length && !data.profiles.includes(form.profile)) {
          setForm(current => ({ ...current, profile: data.profiles[0] }))
        }
      })
      .catch(() => setError('Unable to load local configuration.'))
    refreshRuns()
  }, [])

  useEffect(() => {
    const hasActiveRun = runs.some(run => ['queued', 'running'].includes(run.status))
    if (!hasActiveRun) return undefined
    const interval = window.setInterval(refreshRuns, 2500)
    return () => window.clearInterval(interval)
  }, [runs])

  const selectedSummary = useMemo(
    () => runs.find(run => run.id === selectedRun?.id),
    [runs, selectedRun],
  )

  const onField = event => {
    setForm(current => ({ ...current, [event.target.name]: event.target.value }))
  }

  const startRun = async event => {
    if (event) event.preventDefault()
    setError('')
    setSubmitting(true)
    const body = new FormData()
    body.append('payload', JSON.stringify(form))
    if (oamFile) body.append('oam_file', oamFile)

    try {
      const response = await fetch('/api/runs', { method: 'POST', body })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Unable to start the run.')
      await refreshRuns()
      setPage('history')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  const openRun = async run => {
    const response = await fetch(`/api/runs/${run.id}`)
    if (response.ok) setSelectedRun(await response.json())
  }

  const navigate = nextPage => {
    setSelectedRun(null)
    setPage(nextPage)
  }

  const pages = {
    dashboard: (
      <DashboardPage
        runs={runs}
        onConfigure={() => navigate('configure')}
        onOpenHistory={() => navigate('history')}
      />
    ),
    configure: (
      <ConfigurePage
        form={form}
        config={config}
        oamFile={oamFile}
        error={error}
        submitting={submitting}
        onField={onField}
        onFile={setOamFile}
        onSubmit={startRun}
      />
    ),
    history: (
      <RunHistoryPage
        runs={runs}
        selectedRun={selectedRun ? { ...selectedSummary, ...selectedRun } : null}
        onOpen={openRun}
        onClose={() => setSelectedRun(null)}
      />
    ),
  }

  return (
    <AppLayout activePage={page} onNavigate={navigate} runCount={runs.length}>
      {pages[page]}
    </AppLayout>
  )
}

createRoot(document.getElementById('root')).render(<App />)