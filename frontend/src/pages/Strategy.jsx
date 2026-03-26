import { STINTS } from '../data/mockData.js'
import { Icon } from '../components/Shared.jsx'

function StintTimeline() {
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div className="panel-title">Full-Field Pit Decision Timeline</div>
        <div style={{ display: 'flex', gap: 12, fontFamily: 'var(--font-mono)', fontSize: 9 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 8, background: 'rgba(232,0,45,0.7)', display: 'inline-block' }} />SOFT</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 8, background: 'rgba(234,179,8,0.7)', display: 'inline-block' }} />MED</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 8, background: 'rgba(255,255,255,0.4)', display: 'inline-block' }} />HARD</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 8, border: '1px dashed rgba(255,255,255,0.4)', display: 'inline-block' }} />RL</span>
        </div>
      </div>
      <div style={{ overflowX: 'auto' }}>
        {STINTS.map(s => (
          <div key={s.driver} className="stint-row">
            <div className="stint-row__driver">{s.driver}</div>
            <div className="stint-row__track">
              {s.segs.map((seg, i) => (
                <div key={i} className="stint-seg" style={{ width: `${seg.pct}%`, background: seg.color }} />
              ))}
              {s.pits.map(p => (
                <div key={p} className="stint-pit" style={{ left: `${p}%` }} />
              ))}
              {s.predicted.map(p => (
                <div key={`p${p}`} className="stint-pit stint-pit--predicted" style={{ left: `${p}%` }} />
              ))}
            </div>
          </div>
        ))}
        <div style={{ display: 'flex', paddingLeft: 56, marginTop: 4 }}>
          {['L1','L20','L40','L60','L78'].map(l => (
            <span key={l} style={{ flex: 1, textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--dim)' }}>{l}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

function StrategyPanel() {
  return (
    <div className="card card--red-left">
      <div className="panel-label">Strategy Comparison</div>
      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div style={{ background: 'var(--s0)', padding: 10 }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--dim)', textTransform: 'uppercase' }}>Actual Strategy</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'white', marginTop: 4 }}>2-STOP (S-M-H)</div>
        </div>
        <div style={{ background: 'var(--s0)', padding: 10, borderLeft: '2px solid var(--red)' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--dim)', textTransform: 'uppercase' }}>RL Optimizer</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'white', marginTop: 4 }}>1-STOP (S-H)</div>
        </div>
      </div>
      <div className="panel-label">Predicted Scenarios</div>
      {['Scenario A: Aggressive','Scenario B: Defensive','Scenario C: Fuel Save'].map(s => (
        <button key={s} className="scenario-btn">
          {s}
          <Icon name="chevron_right" style={{ fontSize: 14, color: 'var(--dim)' }} />
        </button>
      ))}
      <button className="execute-btn">EXECUTE BOX THIS LAP</button>
    </div>
  )
}

export default function Strategy() {
  return (
    <div className="grid-12">
      <div className="col-8"><StintTimeline /></div>
      <div className="col-4"><StrategyPanel /></div>
    </div>
  )
}
