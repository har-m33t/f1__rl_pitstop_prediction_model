import { useState, useEffect } from 'react'
import { Icon } from '../components/Shared.jsx'

function StintTimeline({ selectedRace }) {
  const [stints, setStints] = useState([]);
  
  useEffect(() => {
    const fetchStints = async () => {
      try {
        if (!selectedRace) return;
        const res = await fetch(`http://localhost:8000/api/strategy/timeline?year=${selectedRace.year}&track=${selectedRace.track}`);
        const data = await res.json();
        setStints(data.stints || []);
      } catch(e) {
        console.error(e);
      }
    };
    fetchStints();
    const id = setInterval(fetchStints, 3000);
    return () => clearInterval(id);
  }, [selectedRace]);

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
        {stints.map(s => (
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

function PitWindowSimulator({ selectedRace }) {
  const [pitWindow, setPitWindow] = useState(45);
  const [projectedTime, setProjectedTime] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!selectedRace) return;
    const fetchSim = async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`http://localhost:8000/api/simulate_pit_window`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            year: selectedRace.year,
            track: selectedRace.track,
            start_lap: pitWindow,
            end_lap: pitWindow + 4
          })
        });
        const data = await res.json();
        setProjectedTime(data.projected_time);
      } catch (e) {
        console.error(e);
      }
      setIsLoading(false);
    };
    
    const timeoutId = setTimeout(fetchSim, 300);
    return () => clearTimeout(timeoutId);
  }, [pitWindow, selectedRace]);

  const formatTime = (secs) => {
    if (!secs) return '--:--.---';
    const hrs = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = (secs % 60).toFixed(3);
    return `${hrs > 0 ? hrs + ':' : ''}${m.toString().padStart(2, '0')}:${s.padStart(6, '0')}`;
  };

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="panel-title">Pit Window Simulator</div>
      <div className="panel-label">Drag to adjust the target pit window and live-simulate race time via RL environment step() logic.</div>
      
      <div style={{ marginTop: 16, marginBottom: 8 }}>
        <input 
          type="range" 
          min="10" 
          max="70" 
          value={pitWindow} 
          onChange={(e) => setPitWindow(parseInt(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--red)' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--dim)', marginTop: 4 }}>
          <span>LAP 10</span>
          <span style={{ color: 'white', fontWeight: 'bold' }}>Window: L{pitWindow} - L{pitWindow + 4}</span>
          <span>LAP 70</span>
        </div>
      </div>

      <div style={{ background: 'var(--s0)', padding: 12, borderLeft: '2px solid var(--red)', marginTop: 16 }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--dim)', textTransform: 'uppercase' }}>Projected Finish Time</div>
        <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 24, color: isLoading ? 'var(--dim)' : 'white', marginTop: 4, transition: 'color 0.2s' }}>
          {isLoading ? 'Simulating...' : formatTime(projectedTime)}
        </div>
      </div>
    </div>
  );
}

export default function Strategy({ selectedRace }) {
  return (
    <div className="grid-12">
      <div className="col-8"><StintTimeline selectedRace={selectedRace} /></div>
      <div className="col-4">
        <StrategyPanel />
        <PitWindowSimulator selectedRace={selectedRace} />
      </div>
    </div>
  )
}
