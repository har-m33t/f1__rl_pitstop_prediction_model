import { TYRE_COMPOUNDS } from '../data/mockData.js'

function DegCurve({ compound }) {
  const areaPath = compound.points.replace('M', 'M').replace(/^/, '') +
    ` L100,60 L0,60 Z`
  return (
    <div className="deg-card">
      <div className="compound-label">
        <span style={{ width: 12, height: 12, borderRadius: '50%', background: compound.color, display: 'inline-block' }} />
        {compound.name}
      </div>
      <svg viewBox="0 0 100 60" style={{ width: '100%', height: 100 }} preserveAspectRatio="none">
        <path d={areaPath} fill={compound.color} opacity={0.1} />
        <path d={compound.points} fill="none" stroke={compound.color} strokeWidth={2} />
      </svg>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--dim)', marginTop: 8 }}>
        Deg rate: <span style={{ color: compound.color }}>{compound.deg}</span>
        &nbsp;· Life: {compound.life}
      </div>
    </div>
  )
}

export default function Tyres() {
  return (
    <>
      <div className="panel-label">Compound Degradation Model</div>
      <div className="grid-4">
        {TYRE_COMPOUNDS.map(c => <DegCurve key={c.name} compound={c} />)}
      </div>
      <div className="card" style={{ marginTop: 4 }}>
        <div className="panel-title" style={{ marginBottom: 12 }}>Tyre Selection Heatmap</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 10 }}>
            <thead>
              <tr style={{ color: 'var(--dim)', textAlign: 'left' }}>
                {['Driver','Stint 1','Stint 2','Stint 3','Total Stops','RL Suggestion'].map(h => (
                  <th key={h} style={{ padding: '6px 10px', borderBottom: '1px solid rgba(255,255,255,0.05)', fontWeight: 400 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                ['VER','SOFT 28L','MEDIUM 30L','HARD 20L','2','1-STOP feasible'],
                ['LEC','SOFT 28L','MEDIUM 12L','HARD ?','2+','BOX NOW'],
                ['HAM','MEDIUM 42L','HARD 21L+','—','1','STAY OUT'],
                ['NOR','SOFT 55L','HARD ?','—','1','PIT L60'],
              ].map(([driver, ...cells]) => (
                <tr key={driver} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '6px 10px', color: 'white', fontWeight: 700 }}>{driver}</td>
                  {cells.slice(0, 3).map((c, i) => (
                    <td key={i} style={{ padding: '6px 10px', color: 'var(--muted)' }}>{c}</td>
                  ))}
                  <td style={{ padding: '6px 10px', color: 'white' }}>{cells[3]}</td>
                  <td style={{ padding: '6px 10px', color: 'var(--red)' }}>{cells[4]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
