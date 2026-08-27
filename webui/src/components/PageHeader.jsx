export default function PageHeader({ eyebrow, title, description, icon: Icon, actions }) {
  return <header className="page-header">
    <div>
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
    <div className="page-header-actions">
      {actions}
      <div className="header-mark"><Icon size={20} /></div>
    </div>
  </header>
}
