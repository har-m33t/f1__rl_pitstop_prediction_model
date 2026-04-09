// Shared Icon component using Material Symbols
export function Icon({ name, className = '', style = {} }) {
  return (
    <span className={`ms ${className}`} style={style} aria-hidden="true">
      {name}
    </span>
  )
}

// KPI metric tile
export function KpiTile({ label, value, sub, subColor = 'var(--muted)', accent = 'var(--red)', onClick }) {
  return (
    <div className={`kpi ${onClick ? 'kpi--interactive' : ''}`} style={{ borderLeft: `2px solid ${accent}` }} onClick={onClick}>
      <div className="kpi__label">{label}</div>
      <div className="kpi__value">{value}</div>
      {sub && <div className="kpi__sub" style={{ color: subColor }}>{sub}</div>}
    </div>
  )
}

// Telemetry dense tile
export function TelemTile({ label, value, sub, subColor = 'var(--muted)' }) {
  return (
    <div className="telem-tile">
      <div className="telem-tile__label">{label}</div>
      <div className="telem-tile__value">{value}</div>
      {sub && <div className="telem-tile__sub" style={{ color: subColor }}>{sub}</div>}
    </div>
  )
}

// Horizontal performance bar row
export function PerfBar({ name, value, max = 100, color = 'var(--green)' }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--muted)' }}>{name}</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color }}>{value}%</span>
      </div>
      <div className="perf-bar">
        <div className="perf-bar__fill" style={{ width: `${(value / max) * 100}%`, background: color }} />
      </div>
    </div>
  )
}
