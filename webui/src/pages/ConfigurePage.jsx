import { FolderOpen, LoaderCircle, MonitorCog, Play, XCircle } from 'lucide-react'
import Field from '../components/Field'
import PageHeader from '../components/PageHeader'

export default function ConfigurePage({ form, config, oamFile, error, submitting, onField, onFile, onSubmit }) {
  const extended = form.clause === '1.1.1'

  return (
    <>
      <PageHeader 
        eyebrow="Compliance execution" 
        title="Configure a new check" 
        description="Set the target device and requirements for this validation." 
        icon={MonitorCog} 
      />
      <form onSubmit={onSubmit}>
        <section className="panel">
          <div className="panel-title">
            <h2>Session parameters</h2>
            <p>Required device connection and compliance settings.</p>
          </div>
          <div className="form-grid">
            <Field label="Compliance clause">
              <select name="clause" value={form.clause} onChange={onField}>
                {Object.entries(config.clauses).map(([value, label]) => (
                  <option key={value} value={value}>{value} — {label}</option>
                ))}
              </select>
            </Field>
            <Field label="DUT profile">
              <select name="profile" value={form.profile} onChange={onField}>
                {config.profiles.map(profile => (
                  <option key={profile} value={profile}>{profile}</option>
                ))}
              </select>
            </Field>
            <Field label="Device IP / hostname">
              <input required name="ssh_ip" value={form.ssh_ip} onChange={onField} />
            </Field>
            <Field label="SSH username">
              <input required name="ssh_user" value={form.ssh_user} onChange={onField} />
            </Field>
            <Field label="SSH password">
              <input type="password" name="ssh_password" value={form.ssh_password} onChange={onField} />
            </Field>
            <Field label="OAM Excel file">
              <span className="file-input">
                <FolderOpen size={17} />
                <span>{oamFile ? oamFile.name : 'Choose workbook (optional)'}</span>
                <input type="file" accept=".xlsx,.xls" onChange={event => onFile(event.target.files?.[0] || null)} />
              </span>
            </Field>
          </div>
        </section>

        {extended && (
          <section className="panel extended-panel">
            <div className="panel-title">
              <h2>SNMP & web portal</h2>
              <p>Used by clause 1.1.1 secure management protocol checks.</p>
            </div>
            <div className="form-grid three-columns">
              <Field label="SNMPv3 user">
                <input name="snmp_user" value={form.snmp_user} onChange={onField} />
              </Field>
              <Field label="SNMP auth pass">
                <input type="password" name="snmp_auth_pass" value={form.snmp_auth_pass} onChange={onField} />
              </Field>
              <Field label="SNMP priv pass">
                <input type="password" name="snmp_priv_pass" value={form.snmp_priv_pass} onChange={onField} />
              </Field>
              <Field label="SNMP community">
                <input name="snmp_community" value={form.snmp_community} onChange={onField} />
              </Field>
              <Field label="Web login URL">
                <input 
                  name="web_login_url" 
                  placeholder={`http://${form.ssh_ip}/dvwa/login.php`} 
                  value={form.web_login_url} 
                  onChange={onField} 
                />
              </Field>
              <Field label="Web username">
                <input name="web_username" value={form.web_username} onChange={onField} />
              </Field>
              <Field label="Web password">
                <input type="password" name="web_password" value={form.web_password} onChange={onField} />
              </Field>
            </div>
          </section>
        )}

        {error && (
          <div className="error-message">
            <XCircle size={17} />
            {error}
          </div>
        )}

        <div className="action-row">
          <button type="submit" className="primary-button" disabled={submitting}>
            {submitting ? <LoaderCircle className="spin" size={18} /> : <Play size={18} fill="currentColor" />}
            {submitting ? 'Starting check…' : 'Run check'}
          </button>
          <span>Artifacts and logs stay on this machine.</span>
        </div>
      </form>
    </>
  )
}