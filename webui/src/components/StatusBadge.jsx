export default function StatusBadge({ status }) {
  const label = { completed: 'Completed', failed: 'Failed', running: 'Running', queued: 'Queued' }[status] || status
  return <span className={`status ${status}`}>{label}</span>
}
