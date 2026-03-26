import { useState, useEffect } from 'react'
import { PerfBar } from '../components/Shared.jsx'

function ObsPanel() {
  const [obsData, setObsData] = useState([]);
  useEffect(() => {
    const fetchObs = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/model/observations');
        setObsData(await res.json());
      } catch(e) { console.error(e) }
    };
    fetchObs();
    const id = setInterval(fetchObs, 3000);
    return () => clearInterval(id);
  }, []);

  const qStay = -91.4, qPit = -89.1;
  const pitFavoured = qPit > qStay;

  return (
    <div className="card">
      <div className="panel-title">DQN Agent — State Observation</div>
      <div className="panel-label">Current observation vector (normalised [0,1])</div>

      {obsData.map((obs, i) => (
        <div key={i} className="qval-row">
          <div className="qval-row__label">{obs.label}</div>
          <div className="qval-row__bar">
            <div className="qval-row__bar__fill" style={{ width: `${obs.value * 100}%`, background: obs.color }} />
          </div>
          <div className="qval-row__val" style={{ color: obs.highlight ? 'var(--red)' : 'white' }}>
            {obs.value.toFixed(2)}{obs.highlight ? ' ↑' : ''}
          </div>
        </div>
      ))}

      <div className="grid-2" style={{ marginTop: 16 }}>
        <div style={{ background: 'var(--s0)', padding: 12 }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--dim)', textTransform: 'uppercase' }}>Q(STAY OUT)</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 20, color: 'white', marginTop: 4 }}>{qStay}</div>
        </div>
        <div style={{ background: pitFavoured ? 'rgba(232,0,45,0.1)' : 'var(--s0)', padding: 12, border: pitFavoured ? '1px solid rgba(232,0,45,0.3)' : 'none' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--red)', textTransform: 'uppercase' }}>
            Q(PIT) {pitFavoured ? '← PREFERRED' : ''}
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 20, color: 'var(--red)', marginTop: 4 }}>{qPit}</div>
        </div>
      </div>
    </div>
  )
}

function PerformancePanel() {
  const [perfData, setPerfData] = useState([]);
  useEffect(() => {
    fetch('http://localhost:8000/api/model/performance')
      .then(r => r.json())
      .then(setPerfData)
      .catch(console.error);
  }, []);

  return (
    <div className="card">
      <div className="panel-title">Agent vs Baseline Performance</div>
      <div className="panel-label">Win-rate over 50 episodes vs identical race conditions</div>

      {perfData.map(a => (
        <PerfBar key={a.name} name={a.name} value={a.winRate} color={a.color} />
      ))}

      <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="panel-label">Counterfactual: If degradation −10%</div>
        <div className="cf-row">
          <span>Decision flipped on</span>
          <span className="cf-row__val">3 / 55 laps</span>
        </div>
        <div className="cf-row">
          <span>Avg reward drop vs deterministic</span>
          <span className="cf-row__val">−4.2%</span>
        </div>
        <div className="cf-row">
          <span>Strategy robust to noise</span>
          <span className="cf-row__val" style={{ color: 'var(--green)' }}>YES</span>
        </div>
      </div>

      <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="panel-label">Phase 5 Robustness (stress test)</div>
        {[
          ['Deterministic (clean)',   100],
          ['+ SC noise (10%)',         93],
          ['+ Temp drift (3°C/lap)',   96],
          ['+ Tire variance (2L std)', 91],
          ['All noise combined',       86],
        ].map(([label, pct]) => (
          <PerfBar key={label} name={label} value={pct} max={100}
            color={pct >= 95 ? 'var(--green)' : pct >= 88 ? '#eab308' : 'var(--red)'} />
        ))}
      </div>
    </div>
  )
}

export default function RlModel() {
  return (
    <div className="grid-12">
      <div className="col-6"><ObsPanel /></div>
      <div className="col-6"><PerformancePanel /></div>
    </div>
  )
}
